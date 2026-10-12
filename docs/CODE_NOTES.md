# EMS Backend — Code Notes

How the Release 1 backend is built and why. Read this before changing code. For running, deploying and operating the
system see [MAINTENANCE_NOTES.md](MAINTENANCE_NOTES.md).

The spec pack is binding: `spec/EMS_R1_Implementation_Spec_v1.0.md`, `db/*.sql`, `contracts/api-examples.json`.
Section, API, DEC, OD and TASK numbers in the code and here refer to that spec.

---

## 1. Shape of the system

```
            ┌──────────────┐  session cookie / extension bearer
 web app ──▶│  API (FastAPI)│── connects as ems_app ──┐
 extension ─▶│  app/        │                         │
            └──────────────┘                         ▼
                   │ writes rows + outbox_events   PostgreSQL (schema ems, FORCE RLS)
                   ▼                                  ▲
            ┌──────────────┐                         │
            │ Worker        │── connects as ems_worker┘
            │ worker/       │  outbox loop (1 s) + minute tick (APScheduler)
            └──────────────┘
```

- One Docker image runs both processes (`infra/backend.Dockerfile`, DEC-001).
- No ORM models. All queries are explicit parameterised SQL against the canonical schema.
- Python 3.11 only (`requires-python = ">=3.11,<3.12"`); every dependency is pinned (DEC-002).

### Directory map

| Path | Purpose |
|---|---|
| `app/main.py` | `create_app()`: routers, CORS, request middleware, exception handlers. `app` is built lazily on first attribute access so importing never needs env vars. |
| `app/serve.py` | API entry point (`python -m app.serve`): validates settings, then runs uvicorn with proxy headers trusted only from `FORWARDED_ALLOW_IPS`. |
| `app/config.py` | Reads env (Section 34). Refuses to start on missing / half-set / unimplemented settings. |
| `app/health.py` | API-001 `/health`, outside the envelope. |
| `app/platform/` | Cross-cutting pieces every router uses (see §2). |
| `app/auth/` | Sign-up, login, logout, password reset, `/me`, Google OIDC, session cookies. |
| `app/org/` | Company setup, invitations, members, roles (API-010..016). |
| `app/room/` | Live Employee Room: consent, check-in/out, heartbeats, breaks, LiveKit tokens, views (API-017..028). |
| `app/hr/` | Employees, attendance, leave, daily report (API-029..034). |
| `app/projects/` | Projects, Kanban tasks, time entries, kickoff templates (API-038..044). |
| `app/crm/` | Contacts, deals, pipeline, Win, activities, suppression list check (API-045..052). |
| `app/finance/` | Invoices and payments (API-053/054). Records money only. |
| `app/graph/` | Graph memory read API (API-068) and write helpers used by the worker. |
| `app/dashboards/` | Role dashboards (API-067), cached 5 min in `dashboard_cache`. |
| `app/hr/agent.py` | HR Agent (API-035) and versioned HR policies (API-036/037). |
| `app/hunter/` | Lead Hunter API (API-055..060) and `crawler.py`, which the worker runs. |
| `app/rules/` | Rule API (API-061..064), action validation and executor (`service.py`), starter rules. |
| `app/leakage/` | Nightly detector run (`service.py`) and findings API (API-065/066). |
| `app/engine/` | Copy of the pack engine (rules, presence, leakage, robots, scoring, hr_agent). Excluded from ruff. Only change: fact `employee.late_count_7d` for `attendance.late`. |
| `worker/` | Outbox loop, handler registry, notification/graph handlers, scheduled jobs, `automation.py` (rules, nightly run, crawl job). |
| `migrations/` | Alembic. Revisions execute `db/*.sql` verbatim. |
| `tests/` | Integration tests against a throwaway PostgreSQL. |

---

## 2. The platform layer (`app/platform/`)

### Request pipeline — `context.py`
Every authenticated route depends on one of:

| Dependency | Accepts |
|---|---|
| `SessionCtx` | web session cookie only |
| `EitherCtx` | session cookie or extension bearer token |
| `ExtensionCtx` | extension bearer token only |
| `session_user` / `optional_session_user` | signed-in user before an org is chosen (logout, invitation accept, Google) |

`build_ctx()` does, in order:
1. Resolve the principal: `ems.resolve_session(sha256(cookie))` or `ems.resolve_extension_token(sha256(bearer))`.
2. For unsafe methods on a session, check CSRF (`X-CSRF-Token` must equal HMAC(CSRF_SECRET, session hash)).
3. Choose the org: `X-Org-Id` header, else the single active membership; several → `ORG_NOT_SELECTED`.
4. Inactive membership → `423 MEMBER_DEACTIVATED`.
5. `db.set_context(org_id, user_id)` → `set_config('app.org_id' / 'app.user_id', …, true)` (transaction-local).
6. Return `Ctx` with `db`, `settings`, `role`, `org` row, helpers.

`Ctx` helpers you will use in handlers:
- `ctx.require("perm")` → raises 403 or returns the scope (`"all"` / `"team"`).
- `ctx.covers("perm", user_id)` → True if scope is `all`, or `team` and the user is a direct report.
- `ctx.calendar` → company `Calendar` (time zone + work hours).
- `ctx.audit(...)`, `ctx.emit(routing_key, payload)`, `ctx.notify(...)` — all write in the **same transaction**.

### Transactions — `db.py`, `context.py:get_db`
- One connection + one transaction per request. `DbDep` uses `scope="function"` so the commit happens **before** the
  response is sent: a client never sees success for a write that did not commit.
- `Db` wrapper: `execute`, `one`, `all`, `scalar`, `savepoint()`, `set_context()`.
- Use `db.savepoint()` around statements that may hit a unique constraint so the outer transaction survives.
- **Write casts as `CAST(:x AS type)`**, never `:x::type` (SQLAlchemy won't bind it).
- `like_pattern()` escapes `%`/`_` for user search text. `jsonb()` serialises for `CAST(:p AS jsonb)`.
- `transaction(engine)` opens an independent transaction (used for audit rows that must survive a failed request,
  rate limits, and the worker).

### Errors — `errors.py`
- `CATALOGUE` maps every allowed error code to (HTTP status, retryable). `ApiError` with an unknown code raises
  `ValueError` — add new codes to the catalogue first, and only if the spec has them.
- Helpers: `not_found(what)`, `denied(msg)`, `invalid(msg, fields)`, `version_conflict(current)`.
- Records in another company return the same `NOT_FOUND` as missing records (no existence leak).

### Responses — `responses.py`, `serialize.py`
- Success: `{"success": true, "message"?, "data", "meta": {api_version, request_id, timestamp}}` via `ok(...)`.
- Error: `{"success": false, "error": {code, message, retryable, details}, "meta"}`.
- Timestamps are UTC with `Z`; naive datetimes raise. Dates are `YYYY-MM-DD`. Money goes through `money()` → `"5000.00"`.

### Request bodies — `schema.py`
- Subclass `Body`: `extra="forbid"` (unknown fields rejected), strings stripped.
- Types: `Email` (lower-cased), `Money` (decimal string only; floats rejected — DEC-011), `Domain` (normalised),
  `Currency` (`^[A-Z]{3}$`), `ExpectedVersion` (`int >= 0`).

### Optimistic concurrency
Mutable records have a `version` column. Update bodies carry `expected_version`; mismatch →
`version_conflict(current_version)` (409). Patterns are in `org/router.py`, `projects/router.py`, `crm/router.py`,
`hr/router.py`.

### Idempotency — `idempotency.py`
Creating POSTs marked "required" in the contract use:
```python
def create_x(body: XIn, ctx: SessionCtx, idem: IdemKey):
    def handler():
        ...                     # do the work, return ok(...)
    return run_once(ctx, idem, handler)
```
- Key = (org, actor, `METHOD path`, header). Stored 24 h. Same key + different body → `IDEMPOTENCY_KEY_REUSED`.
- Concurrent duplicates block on the primary key until the first commits, then replay.
- Failed requests store nothing, so retries recompute the error.
- Exception: sign-up validates the header but cannot store it (no org yet); unique email/slug make replays safe.

### Rate limits — `ratelimit.py`
`ratelimit.hit(engine, name, subject)` commits on its own connection, so a later failure still counts.

| Name | Limit | Subject |
|---|---|---|
| `login` | 10 / 15 min | email + IP |
| `signup` | 5 / hour | IP |
| `password_forgot` | 3 / hour | email |
| `heartbeat` | 4 / min | work session |
| `hr_agent` | 30 / min | user (reserved for the HR Agent task) |

Storage: `ems.rate_limits` + `ems.rate_limit_hit()` (db/003). Exceeding → 429 with `Retry-After`.

### Permissions — `permissions.py`
Single source of truth for the role matrix (Section 7.2 / DEC-009). Roles: `ceo, cto, cfo, coo, hr, manager, employee`.
Scope `"team"` = the manager's active direct reports. API-009 and API-016 read from this table, so changing it changes
what the client is told too. `DASHBOARD_FOR_ROLE` maps role → dashboard.

### Events, audit, notifications — `events.py`
- `audit()` stores actor, action, record and changed field **names** — never values.
- `emit()` writes to `ems.outbox_events`. Passing a deterministic `event_id` makes scheduled emits replay-safe
  (`ON CONFLICT (id) DO NOTHING`).
- `notify()` inserts in-app notifications (de-duplicated recipients; title truncated to 300 chars).

### Security helpers — `security.py`
- Tokens: `new_token(prefix)` → `(client_token, sha256)`. Only hashes are stored (sessions, invitations, resets,
  extension tokens).
- Passwords: argon2id; 12–128 chars; rejected if in `auth/common_passwords.txt`. `verify_password` always runs one
  argon2 verify (dummy hash for unknown / Google-only users) to keep timing constant.
- CSRF: double-submit; `ems_csrf` cookie is readable by the web app and echoed in `X-CSRF-Token`.

### Calendar — `timeutil.py`
Storage is always UTC. `Calendar(time_zone, work_hours)` gives working days, local day bounds, work start/end,
`minutes_late`, `working_days`. Use it instead of hand-rolling time-zone math.

### Web plumbing — `web.py`, `requestctx.py`
- `RequestMiddleware` adds request ID (`X-Request-Id`), security headers (nosniff, referrer policy, CSP, HSTS on
  https) and writes one JSON access-log line per request with the **route template** (no IDs in paths).
- Exception handlers turn `ApiError`, Pydantic validation errors, 404/405 and unexpected exceptions into the envelope.
- Logs must never contain bodies, cookies, tokens, passwords or emails.

---

## 3. Database

- Canonical SQL lives in `ems/db/`: `001_ems_schema.sql`, `002_ems_settings_tokens.sql`, `003_ems_platform_gaps.sql`,
  `004_ems_pilot_fixes.sql`. Alembic revisions `0001` (= 001 + 002), `0002` (= 003) and `0003` (= 004) execute these files **verbatim** through
  `migrations/sqlfile.py`. Table definitions are never retyped in Python.
- Migrations are forward-only; `downgrade()` raises. Restore from backup instead.
- Roles:

| Role | Login | RLS | Used by |
|---|---|---|---|
| `ems_owner` | yes | owns objects (bypasses RLS) | migrations only — never the app |
| `ems_app` | yes | enforced | API |
| `ems_worker` | yes | enforced | worker |
| `ems_lookup` | no | bypasses | owner of `SECURITY DEFINER` bootstrap functions |

- Every table has `FORCE ROW LEVEL SECURITY`; policies compare `org_id` with `ems.current_org()` (from `app.org_id`).
- Bootstrap functions (`ems.signup_company`, `find_user_for_login`, `resolve_session`, `user_memberships`,
  `accept_invitation`, `resolve_extension_token`, `rate_limit_hit`, `worker_organizations`, …) are the only way to
  touch data before an org context exists.
- The worker can see unpublished `outbox_events` across orgs (IDs only); everything else needs org context.
- `db/003` was added because the contracts need storage/grants that 001/002 lack: rate limits, dashboard cache,
  Google linking, outbox lag, per-org worker listing, worker UPDATE/DELETE grants for sweeper and retention.
- `db/005`: `prospects.contact_id` (API-058 repeat returns the same contact) and indexes for hunts, prospects,
  rule runs and open findings.
- `db/004` (pre-pilot review fixes): outbox retry state (`attempts`, `next_attempt_at`, `dead`) and
  `organizations.leakage_scanned_at` (set by the nightly leakage job; gates the leakage dashboard tiles).
- `db/006` (Alembic `0005`): `stream_consents.webcam` and `work_sessions.camera` for the opt-in live webcam.

---

## 4. Domain modules — key behaviour

### Auth (`app/auth/`)
- Sessions (DEC-012): 12 h, or 30 days with "Keep me signed in". Cookies: `ems_session` (HttpOnly) and `ems_csrf`.
- Sign-up creates user + org + CEO membership in `ems.signup_company`; maps `users_email_key` → `EMAIL_IN_USE`,
  `organizations_slug_key` → `SLUG_TAKEN`.
- Failed logins are audited in a separate transaction so the audit row survives the 401.
- Password forgot: with `EMAIL_PROVIDER=none` **no token is created**; response says `email_delivery: "not_configured"`.
  Same response for known and unknown emails.
- Google (API-007/008): OIDC code flow with state, nonce, S256 PKCE; ID token checked for signature, iss, aud, exp,
  nonce; users matched by `sub`, never email; only relative `return_to` paths; Google never creates a company.

### Room (`app/room/`)
- `work_sessions` holds the **current** presence and task; `presence_segments` holds closed intervals. A segment is
  written only when presence or task changes (`change_presence`).
- No heartbeat for 90 s → `offline`, starting 30 s after the last heartbeat (same rule as `engine/presence.py`).
- `close_session()` is the single path for check-out, auto-close and deactivation: ends breaks, writes the last
  segment, revokes the extension token, and creates one `room` time entry per task from active minutes.
- Extension token lifetime: `min(max(work end today + 2 h, now + 2 h), now + 14 h)` — a 19:30 check-in with work
  ending at 18:00 gets 2 h, not 30 min.
- Auto-close: sessions open 2 h after work end of their start day (worker).
- LiveKit: one room per employee (`ems-{org}-{user}`). Publish token 10 min, screen share only; view token 15 min,
  subscribe only. `can_publish_data=False` and TTL always set explicitly (library defaults are unsafe).
- Each view has its own LiveKit identity, `viewer:{view_id}`. A token TTL only limits *joining*, so ending a view means
  removing the participant through the LiveKit room service (`livekit.remove_viewer`). `stream_views.ended_at` is
  written **only after the removal succeeded** (`service.disconnect_views`).
- Viewers are disconnected when: the viewer ends the view (API-027; 503 `MEDIA_UNAVAILABLE` if LiveKit can't be
  reached, so the client retries); consent is withdrawn; a break starts or is approved; the employee or viewer is
  deactivated. The worker's minute sweep (`service.views_to_disconnect`) also ends views past the token lifetime, while
  live view is switched off, when the employee stopped sharing or the viewer was deactivated, and retries any
  removal that failed in the API. The API never fails an employee's own action because of a failed removal.
- Live viewing returns 403 while `organizations.live_view_enabled = false`; **no API can switch it on** (OD-02).
- **Webcam (product decision, deviates from spec Section 9.1)**: `db/006` adds `stream_consents.webcam` and
  `work_sessions.camera`. The webcam is a separate opt-in on the consent (API-017 `webcam`), live only while checked in,
  never recorded, no audio, paused on breaks, and only while `live_view_enabled` (`service.camera_allowed`). Heartbeats
  report `camera` (API-019); the publish token (API-024 `camera`) adds the `camera` source only with webcam consent.
  A view stays open while the employee shares the screen **or** the webcam (`views_to_disconnect`).
- **CEO video wall**: `POST /room/stream/view-grid` (not in the contract; `room.view_live`, reason required, up to 48
  people) opens one logged view per live employee through the same `_start_view` path as API-026, so each employee is
  notified and each view is audited and ended individually (API-027).
- Repeat check-in from the extension (`device.kind = chrome_extension`, session auth) after a web check-in revokes
  old extension tokens and returns a fresh one (audit `room.extension_attached`); other repeats return the open session.

### HR (`app/hr/`)
- Leave balances come only from the published `leave` policy rules (`annual_days`, …). No policy → balances `None`,
  never guessed.
- Approver routing (`approver_for`): leadership → CEO; else manager if their role can decide leave; else HR; else CEO.
  CEO's own leave → HR. Nobody approves their own leave.
- Day status: `present | on_leave | absent_unexplained | not_checked_in`.

### Projects (`app/projects/`)
- Board transitions: `todo↔active`, `active↔review`, `review→done`, `done→review`.
- First task moved to Active turns a `planned` project `active` (and an onboarding client `active`).
- Cost = minutes/60 × member `cost_rate`; `rates_missing` flags incomplete budgets.
- Kickoff templates (`templates.py`): `website_standard` (12), `mobile_app_standard` (15), `blank` (0). Titles are
  implementation defaults; names and counts are fixed by the spec.

### CRM / Finance
- Contact writes check the suppression list by SHA-256 of normalised email/domain → `SUPPRESSED_CONTACT`.
  Adding entries belongs to the Lead Hunter task.
- Win (API-051) creates client + project (from template) and emits `deal.won`.
- Invoices claim time entries with `UPDATE … WHERE id = ANY(:ids) AND billable AND invoice_id IS NULL` and reject the
  request if the row count differs, so two concurrent invoices can never bill the same entry.
- Finance records invoices and payments only; overpayment → `OVERPAYMENT`. Nothing is sent or collected in R1.

### Dashboards
Every tile names its source. Anything EMS can't source goes under `unavailable` with a reason — **never sample numbers**.
Money uses the company base currency. Cached 300 s per (org, role, period, viewer).
Leakage tiles (`leakage`, `open_findings`, `idle_above_threshold`) go under `unavailable` until
`organizations.leakage_scanned_at` is set, so the board never shows $0 at risk before the first 01:00 scan.

### HR Agent and policies (`app/hr/agent.py`)
- `engine/hr_agent.py` classifies the question (policy patterns first), `SqlRepo` runs the fixed query, the answer lists
  the record IDs used. Unknown questions return `answered: false` with the supported list — nothing is guessed.
- Team questions: CEO, COO, HR company-wide; managers their direct reports only; everyone else is refused by the engine.
  Work summary: self, or the caller's visible people. Names must match one person, or the agent asks for the name.
- Only `intent` and `answered` go to `agent_logs`; never the question. Rate limit `hr_agent` 30/min per user.
- Policies are insert-only versions (`expected_version` = current, 0 for the first). Allowed `rules` keys per topic
  (`POLICY_RULES`); publishing applies them to company settings (grace → `work_hours`, break allowance), and a
  `monitoring` policy bumps `room_policy_version`, so everyone must consent again. Publishing needs `hr.manage` at
  company scope (managers cannot).

### Lead Hunter (`app/hunter/`)
- API-055 validates and normalises seeds (max 200), rejects social networks/search engines (`SOURCE_NOT_ALLOWED`), and
  queues the hunt. The crawl runs in the worker (`worker/automation.crawl_next_hunt`, every 15 s, one hunt at a time).
- Per domain: suppression and CRM check (skipped, counted), `robots.txt` (4xx allow, 5xx/network → nothing crawled),
  then up to 5 pages, 1 request / 5 s per domain (round-robin across domains), 10 s timeout, HTML only, 2 MB cap.
  Every decision goes to `crawl_log`.
- Stored: company name, role addresses (info@, sales@, contact@, hello@ on the site's domain), tech tags, country hint,
  team-size hint, source URL, score + reasons (`engine/scoring.py`). Page text is never stored.
- Each prospect emits `prospect.scored` (rule trigger). Promote (API-058) needs `hunter.use` + `crm.manage`, creates
  company + lead contact once (`prospects.contact_id`). Drafts (API-059) always end with the opt-out line.
- Suppression (API-060) stores SHA-256 only, is idempotent, and marks matching prospects `suppressed` at once.

### Rule engine (`app/rules/`)
- `service.validate` = engine validation + action parameters (recipients the trigger can resolve, known templates,
  allowed flags/finding kinds). Saved rules are always executable.
- Saving a key creates version n+1 and disables older versions. Starter rules (Section 15) are seeded on `org.created`
  and re-checked nightly (missing keys only).
- Triggers: `room.checked_in` (late only) → `attendance.late`; `task.overdue` (hourly); `leave.requested`;
  `prospect.scored` (crawler); `deal.stale` and `invoice.overdue` (nightly, deterministic IDs per day).
- `run_for_event`: one `rule_runs` row per (rule, event); actions in a savepoint (failure → `action_failed`, nothing
  applied); events created by actions carry `chain_depth`, and depth 3 → `skipped_loop`.
- Rule-created tasks without a project go to the internal project "Automation follow-ups".

### Leakage (`app/leakage/`)
- Nightly at 01:00 company time (`platform.nightly` event): all seven detectors from `engine/leakage.py` with default
  thresholds. New fingerprints insert once; a hit on a record with an open finding refreshes it; open findings no
  longer detected resolve automatically (`resolution_note`). Rule-created findings (`rule:` fingerprints) are left alone.
- Sets `organizations.leakage_scanned_at`, which shows the leakage dashboard tiles.
- API-065 lists findings by amount at risk, largest first (the contract example's order); totals count the base currency only.
- API-066: first resolution wins (`ALREADY_RESOLVED`), dismissing needs a note, the note goes to `evidence.resolution_note`.

### Graph memory
`graph_nodes` / `graph_edges` with `valid_from` / `valid_to`; changes close old edges (history kept). Writers are
called only from worker handlers and must be idempotent. Reads filter node kinds by the caller's permissions
(`KIND_READ`).

---

## 5. Worker (`worker/`)

- **Outbox loop** (`main.py`): every 1 s, read up to 100 events that are unpublished, not dead and due
  (`next_attempt_at` empty or past); for each, open a transaction, set the event's org as RLS context, lock the row
  (`FOR UPDATE SKIP LOCKED`), run all handlers, set `published_at` — all in one commit. A failure is recorded on the
  row in a separate transaction: `attempts + 1`, `next_attempt_at = now + min(2^attempts, 300 s)`, and `dead = true`
  at 10 attempts. Retry state is in the database, so failing events never block the rest and counts survive restarts.
- **Registry** (`registry.py`): `@handles("routing.key", ...)` registers a handler `(db, event) -> None`. Other tasks
  (rule engine, Lead Hunter, leakage) plug in here without touching the loop. Handlers must be idempotent.
- **Handlers** (`handlers.py`): notifications for invitations, joins, breaks, leave; graph edges for members,
  projects, tasks, contacts, deals, invoices.
- **Minute tick** (`jobs.py`, APScheduler cron at second 0): for each org (via `ems.worker_organizations()`), in its
  own transaction: presence timeouts, auto-close, view sweep (LiveKit removal, see Room); hourly `task.overdue` events; at 23:30 local
  `platform.hr_daily_report`; at 02:00 local `platform.retention`. Daily jobs use deterministic UUIDv5 event IDs so a
  repeated tick inside the 30-min window never runs them twice. At 01:00 local it emits `platform.nightly`
  (leakage run, starter-rule check, `deal.stale` / `invoice.overdue` events) — see `worker/automation.py`.
- **Lead Hunter job** (`automation.crawl_next_hunt`, every 15 s): claims the oldest queued hunt (or one whose
  heartbeat is 10+ minutes old after a restart) and crawls it outside the outbox transaction.

---

## 6. Conventions checklist for new code

- [ ] Route lives in the module's `router.py`; reusable logic in `service.py`.
- [ ] Comment header `# ---- API-0NN` above the route, matching the contract ID.
- [ ] Body model subclasses `Body`; money is `Money`; versioned updates take `expected_version`.
- [ ] `ctx.require(...)` / `ctx.covers(...)` before reading or writing.
- [ ] Missing or other-company records → `not_found(...)`.
- [ ] Creating POST marked "required" → `run_once(ctx, idem, handler)`.
- [ ] Write `ctx.audit(...)` for state changes; `ctx.emit(...)` for anything the worker or other tasks react to.
- [ ] SQL is parameterised; casts are `CAST(:x AS type)`; identifiers never come from input.
- [ ] Response via `ok(...)`; amounts via `money()`; datetimes UTC-aware.
- [ ] No fake success paths: unconfigured integrations raise their catalogue error (Appendix F rule 4).
- [ ] Add/extend an integration test in `tests/` and check it against `contracts/api-examples.json`.

---

## 7. Implementation decisions (where the spec was silent)

| Topic | Decision |
|---|---|
| `db/003` | Added storage/grants the contracts require but 001/002 don't provide. DB-01..18 still pass. |
| SQLAlchemy models | Not written; would be an unused copy of the schema. |
| Sign-up Idempotency-Key | Validated, not stored (no org yet). |
| Password reset | No token while `EMAIL_PROVIDER=none`; 202 with `email_delivery: "not_configured"`. |
| Invite links | Each invited row includes `invite_link` (copyable links). |
| API-016 | Lists every role holding a permission at any scope, plus `team_scope`. |
| Pipeline errors | 401/403/423/429 can occur on any authenticated route, even if a contract table omits them. |
| Notes without a column | Check-out/manual-time note → `activities`; leave decision note → notification; finding note → `evidence.resolution_note`. |
| Room time entries | Created at check-out/auto-close, one per task. |
| Graph `works_on` | person → project. |
| API-027 failure | Returns 503 `MEDIA_UNAVAILABLE` (retryable) when LiveKit can't remove the viewer; the contract lists only 200/404. |
| Role grants | Nobody changes their own role; only the CEO can give `cto`/`cfo`/`coo` (role change or invitation). Checked after `ONE_CEO_ONLY`. |
| Leakage run marker | `organizations.leakage_scanned_at`, set at the end of each nightly run (`app/leakage/service.run`). |
| Webcam | Opt-in live webcam (see Room); a product-owner decision that deviates from spec 9.1. OD-02 legal review must cover it. |
| Video wall | `POST /room/stream/view-grid` opens one logged, notified view per live employee. |
| Web check-in | Extension repeat check-in gets a fresh token, so the extension can attach to a web check-in. |
| Worker LiveKit config | The worker reads `LIVEKIT_URL/_API_KEY/_API_SECRET` from its own environment (all or none) for the view sweep. |

---

## 8. Web app and Chrome extension

- **Web** (`ems/web/`, Next.js 16.4 App Router, see `web/README.md`): about 35 screens against the real API. `/api/v1/*` is
  rewritten to the API (`EMS_API_ORIGIN`), so cookies are first-party. `src/lib/api.ts` handles the envelope, CSRF,
  idempotency keys and `X-Org-Id`; `src/lib/useApi.ts` loads data (state set only in request callbacks, per React 19 lint);
  money stays a decimal string (`sumMoney` uses integer cents). The SessionProvider guards the signed-in area from `/me`.
- **Extension** (`ems/extension/`, Manifest V3, see `extension/README.md`): popup (sign-in, consent, check-in/out, breaks),
  service worker (30 s heartbeat alarm with `chrome.idle`), Media Session Page (LiveKit screen share), settings. Built
  with `tsc` only; LiveKit's ES module is copied next to the media page. Pure rules live in `src/logic.ts` and are unit-tested.
- **Backend additions for the screens**: read-only `GET /deals`, `/clients`, `/invoices`, `/hunts`, `/room/breaks`, `/org`
  (outside the 70-operation contract; tested in `tests/test_web_lists.py`), and `POST /room/stream/view-grid` (tested in
  `tests/test_webcam.py`). Web pages for them include `/crm/clients`, `/crm/deals`, `/room/wall` (CEO video wall) and
  check-in/check-out on `/room/me`.

## 9. Out of scope

- Web app and Chrome extension (other team members).
- Blocked by owner decisions: live viewing of real employees (OD-02), Chrome Web Store (OD-03), email (INT-003 / OD-09;
  outreach stays a copy-to-mail-client draft, OD-05), any language-model feature (INT-006 / OD-06; the HR Agent is rule-based).
