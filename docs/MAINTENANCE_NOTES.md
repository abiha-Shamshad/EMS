# EMS Backend — Maintenance Notes

How to set up, run, check, deploy and operate the Release 1 backend, and what to watch when changing it.
For how the code works see [CODE_NOTES.md](CODE_NOTES.md).

---

## 1. Local setup

```bash
cd ems/backend
python3.11 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt                         # pinned; Python 3.11 only
cp .env.example .env                                        # fill in values (see §3)
```

Database (disposable PostgreSQL 17 recommended; 16 also works):

```bash
ADMIN_DATABASE_URL=postgresql+psycopg://postgres@localhost:5432/ems alembic upgrade head
```

Run:

```bash
python -m app.serve                            # API on :8000 (needs FORWARDED_ALLOW_IPS, e.g. 127.0.0.1 locally)
python -m worker.main                          # worker (separate process)
```

---

### Web app and extension

```bash
cd ems/web && npm ci && EMS_API_ORIGIN=http://127.0.0.1:8000 npm run dev         # http://localhost:3000
cd ems/extension && npm ci && EMS_ORIGIN=http://localhost:3000 npm run build     # load dist/ unpacked in Chrome
```

Set the API's `APP_BASE_URL` to the web URL and `EXTENSION_ID` to the loaded extension's ID. `EMS_API_ORIGIN` is read
when the web app is **built**: rebuild after changing it. Production: `npm run build && npm start` behind the same domain.

## 2. Checks (same as CI)

Run from `ems/` unless noted. CI is `.github/workflows/ci.yml` (PostgreSQL 17 service, trust auth).

| Check | Command | Expected |
|---|---|---|
| Lint | `cd backend && ruff check app worker migrations tests` | clean |
| Engine tests (G2) | `cd backend/app && python -m unittest engine.tests.test_engine` | 21 pass |
| Spec consistency | `python tools/check_spec.py` | CHK-01..12 pass |
| LiveKit grants | `python tools/check_livekit_tokens.py` | LK-01..03 pass |
| DB checks | apply `db/001`..`006` to a fresh DB, then `PGDATABASE=<db> PGUSER=postgres python db/verify_ems_db.py` | DB-01..18 pass |
| Alembic | `ADMIN_DATABASE_URL=... alembic upgrade head` on an empty DB | applies cleanly |
| Web | `cd web && npm run lint && npm run typecheck && npm test && npm run build` | clean, 45 routes |
| Extension | `cd extension && npm run typecheck && npm run build && npm test` | builds `dist/`, tests pass |
| Integration tests | `cd backend && TEST_ADMIN_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres pytest` | all pass |

Notes:
- Integration tests create and drop their own `ems_test_xxxxxxxx` database. They connect as `ems_app` / `ems_worker`
  **without passwords**, so the server needs trust auth for those roles (sandbox / CI only).
- If `TEST_ADMIN_DATABASE_URL` is unset, pytest skips the integration suite — a green run without it proves nothing.
- **Never** point `verify_ems_db.py` or the tests at a database with real data.

---

## 3. Configuration (spec Section 34)

The API refuses to start on bad config — this is intentional (no fake success paths).

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | yes | API, as `ems_app`. Never `ems_owner` or a superuser (bypasses RLS). |
| `WORKER_DATABASE_URL` | worker | As `ems_worker`. |
| `ADMIN_DATABASE_URL` | migrations | Admin role, one-off migration task only. |
| `APP_BASE_URL` | yes | http(s). Its origin is the CORS origin; `https://` turns on HSTS. Also give it to the **worker**: the Lead Hunter user agent points to `<APP_BASE_URL>/bot` (Section 14.1). |
| `SESSION_COOKIE_SECURE` | default `true` | Only `false` for local http. |
| `CSRF_SECRET` | yes | 64 hex chars: `python -c "import secrets; print(secrets.token_hex(32))"`. Rotating it invalidates every CSRF cookie (users must reload / sign in again). |
| `GOOGLE_CLIENT_ID` / `_SECRET` | both or neither | Empty → `GOOGLE_NOT_CONFIGURED`. |
| `LIVEKIT_URL` / `_API_KEY` / `_API_SECRET` | all or none | Empty → `MEDIA_UNAVAILABLE` for screen share; presence still works. Give the **worker** the same values: its view sweep disconnects viewers through LiveKit. |
| `EXTENSION_ID` | optional | Adds `chrome-extension://<id>` to CORS. |
| `EMAIL_PROVIDER` | `none` only | Anything else stops start-up until INT-003 / OD-09 is implemented. |
| `AI_REPHRASER` | `disabled` only | Anything else stops start-up until INT-006 / OD-06. |
| `LOG_LEVEL` | default `info` | |
| `FORWARDED_ALLOW_IPS` | **yes** (API) | Load balancer addresses/ranges, comma-separated (`10.0.0.0/16`). `app.serve` passes it to uvicorn with proxy headers. `*`, hostnames or empty stop start-up. Locally: `127.0.0.1`. |

Secrets come from the environment / secret store, never git. `.env` is git-ignored.

---

## 4. Deployment

One image for API, worker and migrations (`infra/backend.Dockerfile`, build from `ems/`):

```bash
docker build -f infra/backend.Dockerfile -t ems-backend .
docker run -e ADMIN_DATABASE_URL=... ems-backend alembic upgrade head   # 1. migrate (one-off)
docker run --env-file prod.env ems-backend                              # 2. API (port 8000)
docker run --env-file prod.env ems-backend python -m worker.main        # 3. worker
```

Release order: **migrate → API → worker**. Migrations must be backward-compatible with the running API version
because they run before the new API starts (Section 35).

The image runs as non-root user `ems` (uid 10001). The worker can be scaled to more than one process: event rows
are locked with `FOR UPDATE SKIP LOCKED` and daily jobs have deterministic IDs. Keep the scheduler's minute tick in
mind though — every worker process runs it; the jobs are safe to repeat but it is wasted work.

---

## 5. Operating the system

### Health
`GET /health` (API-001):
- `200 ready` — DB ok and LiveKit reachable.
- `200 degraded` — DB ok, LiveKit unavailable or not configured.
- `503 unavailable` — DB down.
- Callers on a private network also get `checks`: `postgres`, `livekit`, `worker_lag_seconds`.
- LiveKit probe is cached 15 s so load balancer polling doesn't hammer it.

### What to monitor

| Signal | Where | Action |
|---|---|---|
| `worker_lag_seconds` rising | `/health` (private) | Worker down or stuck; check worker logs. |
| `"event marked dead after the last attempt"` (ERROR) | worker logs | A handler failed 10 times; the event has `dead = true` and is never retried on its own. Fix the handler / data, then requeue it (SQL below). |
| `"event handler failed; will retry"` (WARNING) | worker logs | Transient; watch for repeats on the same `event_id`. |
| `"scheduled tick failed"` | worker logs, with `org_id` | One org's minute jobs failed; others continue. |
| `"nightly run"` (INFO) | worker logs, with counts | Leakage run per company: findings created / refreshed / resolved, rule events emitted. Missing at 01:00 → check the worker. |
| `"hunt failed"` | worker logs, with `hunt_id` | The crawl raised; the hunt is `failed`. Users start a new hunt. |
| `"rule action failed"` (WARNING) | worker logs, with rule key | A rule's actions were rolled back and the run recorded as `action_failed` (visible in API-064). |
| `"unhandled error"` | API logs | 500 returned. The client sees the `request_id`; search logs for it. |
| 429 spikes | access logs | Brute force or misconfigured `FORWARDED_ALLOW_IPS`. |

Logs are one JSON object per line: `ts, level, logger, message, request_id, method, route (template), status,
duration_ms, org_id, user_id`. No bodies, tokens, passwords or emails are logged — keep it that way.

### Useful SQL (as admin, read-only)

```sql
-- Unpublished events, oldest first, with retry state
SELECT id, org_id, routing_key, created_at, attempts, next_attempt_at, dead FROM ems.outbox_events
WHERE published_at IS NULL ORDER BY created_at LIMIT 50;

-- Dead events (failed 10 times)
SELECT id, org_id, routing_key, created_at, attempts FROM ems.outbox_events WHERE dead AND published_at IS NULL;

-- Requeue one dead event after fixing its handler (this is a write: run it deliberately)
UPDATE ems.outbox_events SET dead = false, attempts = 0, next_attempt_at = NULL WHERE id = '<event id>';

-- Hunts not finished (a running hunt with no heartbeat for 10 min is resumed by the worker)
SELECT id, org_id, status, stats->>'heartbeat_at' AS heartbeat FROM ems.hunts WHERE status IN ('queued','running');

-- Failed rule runs in the last day
SELECT x.org_id, r.key, x.ran_at FROM ems.rule_runs x JOIN ems.rules r ON r.id = x.rule_id
WHERE x.outcome = 'action_failed' AND x.ran_at > now() - interval '1 day';

-- Live views still open (the minute sweep should end them within a minute of their trigger)
SELECT id, org_id, viewer_id, subject_user_id, started_at FROM ems.stream_views WHERE ended_at IS NULL ORDER BY started_at;

-- Open work sessions older than a day (auto-close should have closed them)
SELECT id, org_id, user_id, started_at, last_heartbeat_at FROM ems.work_sessions
WHERE state = 'open' AND started_at < now() - interval '1 day';
```

Do not hand-edit `published_at` to "fix" a dead event unless you have confirmed its side effects are not needed.

### Scheduled jobs (per company time zone)

| When (company-local) | Job |
|---|---|
| Every minute | Mark silent sessions offline (90 s), auto-close sessions open 2 h after work end, disconnect live viewers that must stop (token expired, live view off, employee not sharing, viewer deactivated) and retry failed removals |
| Every 15 s | Lead Hunter: crawl the oldest queued hunt (one at a time per worker) |
| Every hour (:00) | Emit `task.overdue` per overdue open task (once per task / due date / day) |
| 01:00–01:30 window | Nightly run: leakage detectors, auto-resolve, `leakage_scanned_at`, starter-rule check, `deal.stale` / `invoice.overdue` rule events |
| 23:30–00:00 window | HR daily report notification to CEO, COO, HR |
| 02:00–02:30 window | Retention cleanup |

### Data retention (Section 32)

| Table | Kept for |
|---|---|
| `presence_segments`, `stream_views` | 12 months |
| `agent_logs`, `crawl_log`, `notifications` | 90 days |
| `audit_events` | 24 months |

Changing these is a spec/policy change, not just a code change (`worker/jobs.py: RETENTION`).

### Backups and rollback
Migrations are forward-only (`downgrade()` raises). Roll back by restoring a database backup taken before the
migration, then deploying the previous image. Take a backup before every migration.

---

## 6. Common maintenance tasks

**Add a schema change**
1. Write `db/007_<name>.sql` following the 001–006 conventions: `SET ROLE ems_owner`, `search_path = ems, public`,
   `ENABLE` + `FORCE ROW LEVEL SECURITY` and an `org_isolation` policy on every new table, explicit grants to
   `ems_app` / `ems_worker`, bootstrap functions owned by `ems_lookup` with `REVOKE ALL FROM PUBLIC`.
2. Add `migrations/versions/0006_<name>.py` calling `run_sql_file("007_<name>.sql")`.
3. Add the file to `tests/conftest.py` (its list of SQL files) and to the CI "Database checks" step.
4. Re-run `db/verify_ems_db.py`; all DB checks must still pass.

**Add an endpoint** — follow the checklist in CODE_NOTES §6; add the example to `contracts/api-examples.json` via
`tools/gen_api.py` (then `python tools/check_spec.py`).

**Add a worker reaction** — write a function in `worker/handlers.py` (or your task's module imported by
`worker/main.py`) decorated with `@handles("routing.key")`. It runs in the event's org context and must be
idempotent.

**Change a permission** — edit `app/platform/permissions.py: MATRIX` only. It feeds `ctx.require`, API-009 and
API-016. Update tests in `tests/test_roles_worker_dashboards.py`.

**Add a rate limit** — add to `ratelimit.LIMITS`, call `ratelimit.hit(...)` at the top of the route.

**Upgrade a dependency** — pins are DEC-002. Changing one means re-running every check in §2 (Appendix H).
Changing `livekit-api` requires `tools/check_livekit_tokens.py` to pass; changing `argon2-cffi` must keep argon2id.

**Update the common-password list** — `app/auth/common_passwords.txt`, one per line, `#` comments allowed.

**Update the engine** — `app/engine/` is a copy of the pack engine with one change: `employee.late_count_7d` in
`rules.py` `TRIGGER_FACTS["attendance.late"]` (needed by the starter rule `late_three_times`). When replacing it from a
new pack, keep that fact; run the 21 engine tests and `tests/test_automation.py`.

**Add a rule trigger, action or notification template** — triggers and facts live in `engine/rules.py`; who an action
can address per trigger, templates and allowed flags live in `app/rules/service.py` (`TRIGGER_RECIPIENTS`,
`NOTIFY_TEMPLATES`, `SET_FLAGS`, `FINDING_KINDS`); the facts an event supplies are built in `context_for`. Add the
routing key to `TRIGGER_FOR_EVENT` so the worker runs rules for it.

---

## 7. Things that will bite you

- Connecting the API as `ems_owner` or a superuser silently disables tenant isolation. Always `ems_app` / `ems_worker`.
- `:x::type` in SQL is not bound by SQLAlchemy. Use `CAST(:x AS type)`.
- `set_config(..., true)` is transaction-local. Anything run on a new connection/transaction (rate limits, the
  worker, separate audit transactions) must set its own context.
- Naive datetimes raise in serialisation. Always use `utcnow()` / aware UTC values.
- Money must be `Decimal` from strings. Floats are rejected by design.
- A worker without `LIVEKIT_*` cannot disconnect viewers: with LiveKit configured on the API only, views would never be
  removed by the sweep. Configure both or neither.
- The webcam deviates from spec Section 9.1. Keep its safeguards when changing room code: separate opt-in, only while
  checked in, paused on breaks, no recording, no audio, every view logged with a reason and the employee notified.
- Dead outbox events are not retried by a restart; they need the requeue SQL above.
- Running pytest without `TEST_ADMIN_DATABASE_URL` skips the integration suite and still reports success.
- `ems/EMS_R1_v1.0_pack/` (outside `ems/`) is the original pack; `ems/` is the working copy. Edit `ems/` only.

---

## 8. Open items blocked on owner decisions

| ID | Effect today |
|---|---|
| OD-02 | Live viewing stays off (`live_view_enabled = false`, no API to enable it). This now covers the opt-in live webcam and the CEO video wall: the legal review must approve both before the flag is set. |
| OD-03 | Chrome Web Store publication; `EXTENSION_ID` set manually. |
| OD-09 / INT-003 | No email; password reset tokens are not issued; invitations rely on copyable links. |
| OD-06 / INT-006 | No language-model features; the HR Agent is pattern-based. |
| OD-05 / INT-003 | Outreach is a draft the user copies to their own mail client; no sending or sequences. |
| — | Repeat check-in from the extension after a web check-in cannot get an extension token (product decision needed). |
