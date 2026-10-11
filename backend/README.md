# EMS backend (Release 1)

FastAPI API service + one worker process over PostgreSQL with FORCE row-level security, built from the binding
`EMS_R1_v1.0_pack` (spec `../spec/EMS_R1_Implementation_Spec_v1.0.md`, schema `../db/`, contracts `../contracts/api-examples.json`).

## Scope

Implemented: TASK-001..007, 009, 010, 014, the API side of TASK-011 (publish/view tokens), the HR part of TASK-008,
dashboards from TASK-015, retention/rate limits/headers from TASK-017. **55 of the 70 operations**:

| Area | Operations |
|---|---|
| System and authentication | API-001..009 |
| Company and team | API-010..016 |
| Live Employee Room | API-017..028 |
| People and HR | API-029..034 |
| Projects and tasks | API-038..044 |
| CRM, client lifecycle, invoices, payments | API-045..054 |
| Dashboards, graph memory, notifications | API-067..070 |

Not in this backend (owned by other tasks): HR Agent and HR policies API-035..037, Lead Hunter API-055..060,
rule engine API-061..064 and starter rules, leakage job and API-065/066 (Wajiha); web app and Chrome extension (Andleeb).
Their tables exist; the worker exposes `worker.registry.handles(...)` so those handlers plug in without changing the loop.

## Layout

```
app/
  main.py            create_app(): routers, middleware, exception handlers
  config.py          Section 34 settings; refuses to start on missing/unimplemented settings
  health.py          API-001
  platform/          request pipeline (context.py), envelope, errors (Section 33), idempotency, rate limits,
                     audit/outbox/notifications, pagination, company calendar, security, notifications API
  auth/  org/  room/  hr/  projects/  crm/  finance/  graph/  dashboards/
  engine/            verbatim copy of the pack engine (rules, presence, leakage, robots, scoring, hr_agent) + its tests
worker/              outbox loop (main.py), handler registry, notification + graph handlers, per-timezone jobs
migrations/          Alembic: 0001 = db/001 + db/002 verbatim, 0002 = db/003
tests/               integration tests against a disposable PostgreSQL (TEST-001 shape checks, G8, G9, role matrix)
```

## Run

```bash
pip install -r requirements-dev.txt                       # Python 3.11, pinned versions (DEC-002)
ADMIN_DATABASE_URL=postgresql+psycopg://postgres@host/ems alembic upgrade head
cp .env.example .env                                      # fill in; API connects as ems_app, worker as ems_worker
FORWARDED_ALLOW_IPS=<load balancer range> uvicorn app.main:app --proxy-headers
python -m worker.main

# checks
(cd app && python -m unittest engine.tests.test_engine)   # 21 engine tests
TEST_ADMIN_DATABASE_URL=postgresql://postgres@127.0.0.1:5432/postgres pytest   # creates and drops its own database
```

## Decisions where the spec was silent or inconsistent

| Topic | What this code does | Why |
|---|---|---|
| `db/003_ems_platform_gaps.sql` | Adds `rate_limits` + `ems.rate_limit_hit()`, `dashboard_cache`, `ems.link_google()`, `ems.pending_invitation_exists()`, `ems.outbox_lag_seconds()`, `ems.worker_organizations()`, and worker grants (`UPDATE(ended_at)` on stream_views, `DELETE` for retention) | The contracts require these behaviours but 001/002 give no storage or permission for them (same pattern as 002). DB-01..18 still pass, including DB-15 |
| SQLAlchemy models | Not written; all queries are explicit parameterised SQL against the canonical schema | TASK-002 asks for models "mirroring columns"; they would be an unused second copy of the schema. Easy to add if the team wants them |
| Sign-up Idempotency-Key | Header required and validated, but not stored | `idempotency_keys` is scoped to an existing company; replays are still safe (unique email/slug -> `EMAIL_IN_USE`) |
| Password reset | No token is created while `EMAIL_PROVIDER=none`; response 202 adds `email_delivery: "not_configured"` | A token that can never reach its owner is a fake success path (Appendix F rule 4) |
| Invite links | Each invited row includes `invite_link` | Section 3.2 AUD-03 / API-011 "copyable links"; the example JSON omits the field |
| API-016 | Matrix lists every role holding a permission at any scope, plus `team_scope` | The example lists `manager` under leave.decide but not hr.manage although both are team-scoped |
| Pipeline-level errors | 401/403/423/429 can occur on any authenticated route | Several contract tables (e.g. API-053) omit 403 although the route needs a permission |
| Notes without a column | Check-out note and manual-time note -> `activities`; leave decision note -> employee notification; finding resolution note -> `evidence.resolution_note` | The schema has no note columns for these |
| Project status | First task moved to Active turns a `planned` project `active` (and an onboarding client `active`) | No other operation changes project status in Release 1 |
| Room time entries | Created at check-out / auto-close, one per task, from active segments | Same minutes as "at task switch"; one code path |
| Repeat check-in | Returns the open session without a new extension token (per contract) | If the web app checked in first, the extension cannot obtain a token: needs a product decision |
| Graph `works_on` | person -> project | Section 16 allows project or task; the API-068 example shows projects |
| Live view off | API-024/026 return 403 while `live_view_enabled = false`; no API can switch it on | OD-02 legal gate |

## Security notes

Tenant isolation is enforced by PostgreSQL RLS (`set_config` per transaction, ems_app/ems_worker only); sessions and
all tokens are stored as SHA-256; argon2id passwords with a common-password list; double-submit CSRF bound to the
session; rate limits committed independently of the request; strict request bodies (unknown fields rejected, money as
decimal strings); no secrets or bodies in logs; Google sign-in validates signature, iss, aud, exp, nonce, state, PKCE
and only accepts relative `return_to` paths.
