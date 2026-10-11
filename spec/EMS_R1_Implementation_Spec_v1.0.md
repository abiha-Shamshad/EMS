---
brand: "EMS"
title: "EMS - Employee Management System"
subtitle: "Release 1 - Company Workspace, Live Employee Room, People & HR Agent, Projects, CRM & Client Lifecycle, Lead Hunter, Rules Engine, Graph Memory & Revenue Leakage"
tagline: "Verified implementation specification written from the EMS Implementation Report, four approved screens and the CEO product direction"
---

| Document item | Binding value |
|---|---|
| Document code | EMS-R1-IMPL-1.0.0 |
| Readiness status | PARTIALLY READY - TASK-001 to TASK-017 ready to implement; live screen streaming to real employees (OD-02), Chrome Web Store publication (OD-03), automatic email (INT-003), Lead Hunter outreach at scale (OD-05) and any language-model feature (INT-006) are BLOCKED until their owner decisions close (Appendix C) |
| Product | EMS - one workspace where a company runs its people, work, clients and revenue, with a live room for leadership |
| Delivery model | Multi-company SaaS product: every company is an isolated organization in one deployment |
| Release | Release 1 of 2 - first pilot company |
| Public API root | /api/v1 |
| Frontend | Next.js 16.4.0 (App Router) + TypeScript, responsive web; Chrome extension (Manifest V3) for the Employee Room |
| Backend | Python 3.11 + FastAPI 0.143.0 + Pydantic 2.14.0 + SQLAlchemy 2.1.4 + Alembic 1.20.0 + psycopg 3.3.6 - one modular service plus one worker process |
| Database | PostgreSQL 17 on AWS RDS with FORCE row-level security; schema verified on PostgreSQL 16.13 (Appendix H) |
| Async | PostgreSQL outbox + worker process + APScheduler 3.11.3 for nightly jobs; no Redis or message broker in Release 1 (DEC-004) |
| Live media | Self-hosted LiveKit server (Apache 2.0) + livekit-api 1.2.1 (tokens) + livekit-client 2.22.4 + @livekit/components-react 2.9.24 |
| Authentication | EMS email + password (argon2id) and Google sign-in (OpenID Connect) |
| AI | Rule-based: JSON rule engine, deterministic HR Agent, scoring and leakage detectors, graph memory in PostgreSQL. No external AI API calls in Release 1 (DEC-007) |
| Hosting reference | AWS: 2 API containers, 1 worker container, RDS PostgreSQL, one LiveKit host, S3 for static assets |
| Specification date | 10 October 2026. No release date is set by this document (OD-08). |

::: callout-green
Binding product decision

EMS replaces the separate tools a growing company stitches together (a ClickUp-style work tool, a GoHighLevel-style CRM, an HR tool and a monitoring tool) with one system that answers the CEO's three daily questions: Who is working on what right now? Which clients and deals need action? Where is money leaking? Release 1 delivers one complete path for each question, with logic the company can read and audit, and without paying for AI calls on every click.
:::

::: callout-red
MANDATORY TRUST NOTE - READ BEFORE IMPLEMENTATION

The Employee Room watches people. It must never capture anything silently: an employee sees a notice, consents, picks the screen in Chrome's own picker and sees every time someone views it. No recording, keystrokes, webcam, microphone or browsing history in Release 1. Live screen viewing of real employees stays switched off (`live_view_enabled = false`) until the company completes OD-02. One company must never see another company's data. Never show a metric that EMS cannot source - show it as unavailable instead.
:::

::: callout-blue
Start here

Status: PARTIALLY READY. Developers start with TASK-001 in Appendix E and follow the task order. AI coding tools get the handoff text in Appendix F. What was actually verified is in Appendix H; nothing in this document claims the application is built. Owner decisions needed first: the must-work tier and demo date (OD-01, OD-08), the monitoring legal review (OD-02) and how the extension is distributed (OD-03).
:::

# 1. Executive Scope and Architectural Intent

EMS is a business operating system for companies of roughly 10 to 200 people. Release 1 is one Python service, one worker, one PostgreSQL database, one media server and one Chrome extension. That is small enough for the current team (one backend developer) to build and run.

-   **Live Employee Room:** check-in, presence (active, idle, locked, on break, offline), current task, breaks and a CEO live grid with consented, audited screen viewing.

-   **People and HR Agent:** directory, attendance from real sessions, leave with overlap protection, policies, and an HR Agent that answers questions from EMS records and never guesses.

-   **Work:** projects, Kanban tasks and time that comes automatically from the Room, so billable work is not lost.

-   **Clients:** contacts, deals, pipeline, and one "Win" action that creates the client and the kickoff project together - the client lifecycle cannot break between sales and delivery.

-   **Lead Hunter:** EMS's own polite crawler over company websites the user supplies, robots.txt compliant, with transparent ICP scoring and outreach drafts.

-   **Automation without API bills:** a JSON rule engine, graph memory in PostgreSQL and deterministic detectors. Every decision has a visible reason.

-   **Revenue and leakage engine:** nightly detectors for unbilled time, overdue invoices, stale deals, won deals without a project or invoice, budget overruns and idle paid time, each with an amount and evidence.

::: callout-orange
What "AI" means in Release 1

The product promise is "AI and super sustainable". Release 1 meets it with rules, scoring, graph traversal and templates that run inside EMS at zero marginal cost and give the same answer every time. A language-model adapter is defined (INT-006) but disabled and BLOCKED: it may later rephrase answers, but never decide them. This keeps costs predictable and makes every automated action explainable to the CEO.
:::

# 2. Product Scope, Users and the Complete Journey

## 2.1 Users

| Role | Uses EMS to | Release 1 home screen |
|---|---|---|
| CEO | See the live room, approve leave, see pipeline, revenue at risk and every dashboard | CEO dashboard |
| CTO | Run engineering projects, tasks, automation rules | CTO dashboard |
| CFO | Record invoices and payments, budgets, leakage | CFO dashboard |
| COO | Operations: live room, HR overview, projects, CRM | COO dashboard |
| HR | Directory, attendance, leave, policies, HR Agent | HR dashboard |
| Manager | Lead a team: approve team leave and breaks, assign tasks, own deals | Employee dashboard + team panels |
| Employee | Check in, work on tasks, request leave and breaks, see who viewed their screen | Employee dashboard |

## 2.2 The Release 1 journey (one complete path)

1.  Imran (CEO) creates the company account, completes company setup and invites the team (screens 01, Create Company Account, Company Setup, 06).
2.  Bilal (employee) accepts, installs the extension, reads the monitoring notice and consents.
3.  At 09:02 Bilal checks in and picks Task "Auth API"; the extension reports presence every 30 seconds.
4.  Imran opens the live grid, sees 12 people checked in and opens Bilal's screen with a reason. Bilal's extension shows "Imran Qureshi is viewing your screen".
5.  Usman (manager) wins the Northwind deal: EMS creates the client and the kickoff project in one action.
6.  Bilal's Room time on Northwind tasks becomes time entries; Omar (CFO) records invoice INV-2026-1048.
7.  At 01:00 the nightly leakage run finds an overdue invoice, a stale deal and 3 unbilled hours; the CEO and CFO see $8,620.00 at risk with evidence and resolve them.
8.  HR asks the HR Agent "Who is on leave today?" and gets an answer with sources.

## 2.3 In scope and non-goals

| In Release 1 | Not in Release 1 (reason) |
|---|---|
| Company signup, setup, invitations, roles (7 fixed roles) | Custom roles (report Week 2) |
| Chrome extension: consent, check-in/out, presence, breaks, screen sharing page | Recording history, multi-monitor view (report Week 2; OD-02) |
| CEO live grid, audited live view, "who viewed me" | Webcam, microphone, keystroke or URL tracking (never planned) |
| Directory, attendance, leave, break log, daily report, policies | Payroll and salary (report Week 2) |
| HR Agent (rule-based, sourced answers) | Free-text AI chat (INT-006 BLOCKED) |
| Projects, Kanban, tasks, manual and Room time | Gantt timeline (report Week 2) |
| Contacts, deals, pipeline, win -> client -> project, activities, invoice and payment records | Email sync, sending invoices, online payments (report Week 2 / "Billing (future)") |
| Lead Hunter over user-supplied domains, scoring, drafts, suppression | LinkedIn sources, email sequences, campaigns (OD-05) |
| Rule engine, simulator, run logs | Client-facing workflow builder (report Week 2) |
| Leakage detectors, six role dashboards with sourced metrics | Uptime, deployments and expense metrics (no data source - Section 18) |

# 3. Inputs, Source of Truth and Input Audit

## 3.1 Inputs read

| ID | Input | Coverage | Role in this document |
|---|---|---|---|
| SRC-001 | EMS_Implementation_Report.docx (PMO, Innovation Hub, "Planning stage") | All 8 sections read | Module and screen list, team, risks, open decisions |
| SRC-002 | EMS_Screen_01_Login | Full image | Sign-in contract (email, password, keep me signed in, forgot password, Google, create account) |
| SRC-003 | EMS_Screen_06_Invite | Full image | Invitation contract (rows of email + role, message up to 300 characters, 3-step onboarding) |
| SRC-004 | EMS_Screen_08_CTO_Dashboard | Full image | CTO dashboard layout; metric sourcing audit |
| SRC-005 | EMS_Screen_09_CFO_Dashboard | Full image | CFO dashboard layout; metric sourcing audit |
| SRC-006 | CEO product direction (chat, 2026) and answers: multi-company SaaS; live screen stream; FastAPI + PostgreSQL + Next.js; own scraper | Full | Product intent and binding choices |

Precedence: SRC-006 (CEO direction) decides intent; screens decide layout and fields; official provider documentation decides external behaviour (Appendix G); executed checks decide what is proven (Appendix H). There is no existing repository, so every file path in this document is proposed.

## 3.2 Input audit findings

| ID | Finding | Type | Resolution in this document |
|---|---|---|---|
| AUD-01 | Report: 45 screens with working logic in 7 days; the report itself calls this "very aggressive" and asks for a must-work tier | Confirmed scope risk | Must-work tier in Section 5; dates left to OD-08 |
| AUD-02 | Invite screen offers role "Manager"; the report's role list has CEO, CTO, CFO, COO, HR, Employee only | Contradiction | `manager` added as a seventh role (DEC-009) |
| AUD-03 | Invite screen: "Invited teammates will receive an email" but no email provider is chosen | Missing dependency | Copyable invite links until INT-003 is chosen; text changes to "share this link" while email is off |
| AUD-04 | CTO dashboard shows system uptime, incidents, deployments and latency; nothing in EMS produces these numbers for a customer company | Unsupported metric | Shown as "unavailable - connect a source" in Release 1 (Section 18) |
| AUD-05 | CFO dashboard shows operating expenses, net profit, payroll and bill transactions; EMS has no expense or payroll data in Release 1 | Unsupported metric | Revenue, collections, outstanding and leakage come from EMS records; expenses and profit unavailable |
| AUD-06 | CFO screen: "Outstanding invoices $28.7K - 7 overdue invoices" versus "Financial attention: 7 invoices - $12,450 outstanding" | Internal inconsistency | Design must use one definition: outstanding = all unpaid; overdue = unpaid past due date (Section 18) |
| AUD-07 | CFO budget panel: 31.2K + 18.4K + 12.8K of 40K + 30K + 20K is 69% used, the panel says 72% | Internal inconsistency | Overall ratio is computed, never typed (Section 18) |
| AUD-08 | Report lists "Integration and API Key Settings" and "Automation Dashboard and API Usage" while the CEO wants an API-light system | Clarified | Release 1 screen shows external API calls per week (0 by default) and integration status; no third-party keys stored in Release 1 |
| AUD-09 | Report open decision "Employee Room type (presence board, 2D office, or activity tracker)" | Resolved by CEO | Live screen/video stream with presence board (DEC-005), subject to OD-02 |
| AUD-10 | Report: "Apollo API (paid) versus building the lead tool ourselves" | Resolved by CEO | Own crawler with strict sourcing rules (DEC-010); report Week 2 "LinkedIn sources" conflicts with LinkedIn's robots.txt and terms, moved to OD-05 |
| AUD-11 | Report: Chrome extension "is the highest risk item" | Confirmed | Chrome rules researched (EV-001, EV-002, EV-008, EV-009); design in Section 9; distribution OD-03 |
| AUD-12 | Report: one backend developer serves nearly every module | Confirmed staffing risk | Tasks ordered so Wajiha owns engine code (already drafted and tested) and Abiha owns API/DB |
| AUD-13 | Both dashboard designs label their figures "Illustrative sample metrics/financial data" | Correct practice | Keep: sample data is allowed in design files only, never in the built product |

# 4. Requirements Traceability

| ID | Requirement (source) | Delivered by |
|---|---|---|
| REQ-001 | Multi-company SaaS with company signup and onboarding (SRC-006, SRC-002, SRC-003) | API-002, API-010..012, Section 7 |
| REQ-002 | Sign in with email/password, keep me signed in, forgot password, Google (SRC-002) | API-003..008 |
| REQ-003 | Seven roles with a permission matrix (SRC-001 module 9, SRC-003) | Section 7.2, API-013..016 |
| REQ-004 | Live Employee Room: check-in/out, presence, breaks, current task (SRC-001 module 3) | API-017..023, Section 9 |
| REQ-005 | CEO live grid and full-screen live view (SRC-006 "live screen/video stream") | API-024..028, Section 9.5 |
| REQ-006 | HRM: directory, attendance, leave, break log, reports (SRC-001 module 4) | API-029..034, Section 10 |
| REQ-007 | HR Agent that manages employees and reports to the CEO (SRC-006) | API-035..037, Section 11 |
| REQ-008 | ClickUp-style projects, Kanban, tasks, time (SRC-006, SRC-001 module 5) | API-038..044, Section 12 |
| REQ-009 | GoHighLevel-style CRM and complete client life cycle (SRC-006, SRC-001 module 6) | API-045..054, Section 13 |
| REQ-010 | Client hunter with own scraper (SRC-006) | API-055..060, Section 14 |
| REQ-011 | Rule-based automation, logic over API calls (SRC-006, SRC-001 module 8) | API-061..064, Section 15 |
| REQ-012 | Graph memory instead of AI API calls (SRC-006) | API-068, Section 16 |
| REQ-013 | Revenue engine that stops leakage and uplifts revenue (SRC-006) | API-065..066, Section 17 |
| REQ-014 | Six role dashboards (SRC-001 design note, SRC-004, SRC-005) | API-067, Section 18 |
| REQ-015 | Notifications and confirmation states (SRC-001 modules 2 and 9) | API-069..070, Section 31 |
| REQ-016 | Python backend, AWS RDS, CI/CD to beta and production (SRC-001 section 1) | Sections 6, 35 |

# 5. Release Plan and Must-Work Tier

The report's 7-day plan is not adopted as a commitment (AUD-01). This document fixes the order and the must-work tier; the PMO sets dates (OD-08).

| Tier | Meaning | Modules |
|---|---|---|
| Tier 1 - must work end to end in the demo | Real data, real API, tests pass | Auth and onboarding, roles, Employee Room presence and check-in (without live screen if OD-02 is open), HRM attendance and leave, Projects and Kanban, CRM pipeline with Win, Leakage findings, CEO dashboard |
| Tier 2 - working, narrower | Real API, fewer screens | HR Agent, Rule engine with 3 starter rules, Lead Hunter on up to 50 domains, CFO and HR dashboards |
| Tier 3 - UI with clearly marked limits | Real API where it exists; unavailable tiles labelled | CTO and COO dashboards, Integration settings, live screen view (staff demo accounts only until OD-02) |

Release 2 (Appendix B) adds the report's Week 2 list after Release 1 passes its no-go gates (Section 36).

# 6. Architecture and Binding Decisions

## 6.1 Runtime topology

| From | To | Protocol | Carries |
|---|---|---|---|
| Browser (Next.js web app) | API (FastAPI, 2 containers) | HTTPS | All screens; session cookie |
| Chrome extension (popup, Media Session Page) | API | HTTPS | Consent, check-in, heartbeats, breaks; extension token |
| Media Session Page | LiveKit server | WebRTC | Employee screen track (publish only) |
| CEO / COO browser | LiveKit server | WebRTC | One employee's screen (subscribe only) |
| API | LiveKit | none (token signing only) | Short-lived access tokens signed with the API secret |
| API and worker | PostgreSQL 17 (RDS) | TLS | All data; RLS per company; outbox rows |
| Worker (1 container) | Company websites | HTTPS | Lead Hunter crawl (robots.txt first) |

## 6.2 Decisions

| ID | Decision | Why | Consequence if reversed |
|---|---|---|---|
| DEC-001 | One modular FastAPI service + one worker, one PostgreSQL | One backend developer; simplest thing that works | More services = more deploys and failure modes |
| DEC-002 | Python 3.11, FastAPI 0.143.0, SQLAlchemy 2.1.4, Alembic 1.20.0, Pydantic 2.14.0, psycopg 3.3.6, uvicorn 0.54.0 (versions in EV-013) | CEO choice; report says "advanced Python" | Version changes need re-running Appendix H checks |
| DEC-003 | Tenant isolation by PostgreSQL FORCE RLS + `set_config('app.org_id', ...)` per transaction | A missed WHERE clause cannot leak another company's data (DB-01, DB-02) | Isolation would depend on every query being right |
| DEC-004 | No Redis or broker: outbox table + worker loop (1 s poll) + APScheduler for nightly jobs; rate limits in PostgreSQL | Fewer moving parts; volumes are small (one heartbeat per employee per 30 s) | Add Redis only when measured load needs it |
| DEC-005 | Employee Room = presence board + live screen view via self-hosted LiveKit; one LiveKit room per employee | CEO answer; per-employee rooms mean a viewer token reaches one person only (LK-01..03) | A shared room would let any viewer subscribe to everyone |
| DEC-006 | Screen sharing runs in an extension tab, the "Media Session Page", started by the employee's click (`getDisplayMedia`) | Chrome requires a user gesture and a picker every time (EV-001); a tab page satisfies both with documented behaviour | Offscreen-document capture is a spike only (TASK-011 step 6) |
| DEC-007 | No external AI API in Release 1; rules, scoring, templates and graph queries in EMS | CEO: "logic based custom logics and rule based ai and graph memory for not api calling" | Costs and non-deterministic answers |
| DEC-008 | Graph memory = `graph_nodes` / `graph_edges` tables + recursive SQL, max depth 3 | Uses existing PostgreSQL and RLS; no second database (DB-11) | A graph database would need its own isolation |
| DEC-009 | Seven fixed roles: ceo, cto, cfo, coo, hr, manager, employee | Report roles + Manager from the invite screen (AUD-02) | Custom roles are Release 2 |
| DEC-010 | Lead Hunter crawls only domains the user supplies; RFC 9309 robots rules; no search engines or social networks; role emails only | Legal and reliability risk named in the report (risk 5) | OD-05 needed before any wider sourcing |
| DEC-011 | Money stored as numeric(14,2) with ISO currency; amounts as decimal strings in JSON | No float rounding in revenue | - |
| DEC-012 | Sessions are opaque cookies (32 random bytes, SHA-256 stored); no JWT for the web app | Immediate revocation (DB-04) | JWT cannot be revoked without a list |

# 7. Tenancy, Authentication and Roles

## 7.1 Request pipeline

1.  Resolve the session: hash the `ems_session` cookie and call `ems.resolve_session()` (or `ems.resolve_extension_token()` for the extension).
2.  Choose the organization: `X-Org-Id` if sent, else the only active membership; 403 `ORG_NOT_SELECTED` if several.
3.  Load the membership (role, status) through `ems.user_memberships()`; 423 `MEMBER_DEACTIVATED` if deactivated.
4.  Open a transaction as `ems_app` and run `SELECT set_config('app.org_id', $1, true), set_config('app.user_id', $2, true)`. `SET LOCAL` cannot take bind parameters; `set_config(..., true)` is transaction-local.
5.  Check the permission (7.2) in the route dependency, then run the handler.

Signup and invitation acceptance run before an organization context exists, through SECURITY DEFINER functions owned by `ems_lookup` (DB-03, DB-05, DB-16).

## 7.2 Role permission matrix

| Permission | ceo | cto | cfo | coo | hr | manager | employee |
|---|---|---|---|---|---|---|---|
| room.self (check in, breaks, my viewers) | yes | yes | yes | yes | yes | yes | yes |
| room.view_live (grid, open a screen) | yes | - | - | yes | - | - | - |
| hr.manage (directory, attendance, reports, policies) | yes | - | - | yes | yes | team only | - |
| leave.decide | yes | - | - | - | yes | team only | - |
| members.manage (invite, roles, deactivate) | yes | - | - | - | yes | - | - |
| projects.manage | yes | yes | - | yes | - | yes | - |
| crm.manage | yes | - | - | yes | - | yes | - |
| finance.manage (invoices, payments, cost rates) | yes | - | yes | - | - | - | - |
| hunter.use | yes | - | - | yes | - | yes | - |
| rules.manage | yes | yes | - | yes | - | - | - |
| leakage.read | yes | - | yes | yes | - | - | - |
| leakage.resolve | yes | - | yes | - | - | - | - |
| dashboards.all | yes | - | - | - | - | - | - |

Every member can work on tasks they are assigned, request leave and breaks, and ask the HR Agent about themselves. Nobody can approve their own leave. CFO has read access to contacts and pipeline (API-046, API-047, API-049).

## 7.3 Sessions and Google sign-in

-   Web session: 12 hours, or 30 days with "Keep me signed in". CSRF: double-submit token in `X-CSRF-Token` on POST, PUT, PATCH, DELETE.
-   Extension token: issued at check-in, valid until 2 hours after the company's work end (maximum 14 hours), revoked at check-out or deactivation (DB-17).
-   Google sign-in follows Google's OpenID Connect documentation (EV-006, EV-007): authorization code flow with `state`, `nonce` and S256 PKCE; validate signature from `jwks_uri` `https://www.googleapis.com/oauth2/v3/certs`, `iss` (`https://accounts.google.com` or `accounts.google.com`), `aud`, `exp`; identify the user by `sub`. Google alone never creates a company: it signs in an existing user or one with a pending invitation.

# 8. Data Model and Ownership

The canonical schema is `db/001_ems_schema.sql` plus `db/002_ems_settings_tokens.sql` (both executable, applied and verified - Appendix H). Do not copy table definitions into application code; generate Alembic revision 0001 from these files (TASK-002).

| Area | Tables | Written by | Read by |
|---|---|---|---|
| Identity and tenancy | organizations, users, auth_sessions, memberships, invitations, password_resets | Auth module through bootstrap functions | All modules |
| Employee Room | stream_consents, work_sessions, presence_segments, breaks, stream_views, extension_tokens | Room module | HRM, leakage, dashboards, HR Agent |
| People | leave_requests, hr_policies | HRM module | HR Agent, Room (on-leave check) |
| CRM and clients | companies, contacts, deals, clients, activities | CRM module | Leakage, graph, dashboards |
| Work and money | projects, tasks, time_entries, invoices, payments | Projects and finance modules | Leakage, dashboards |
| Lead Hunter | hunts, prospects, crawl_log, suppression_list | Worker (crawler) and Hunter module | CRM (promote) |
| Automation and memory | rules, rule_runs, leakage_findings, graph_nodes, graph_edges, agent_logs | Worker and engine modules | Dashboards, CRM, HR Agent |
| Platform | notifications, audit_events, outbox_events, idempotency_keys | All modules (one transaction with the business write) | Worker |

Invariants (each has a check): one open work session per employee (DB-06); one active CEO per company (DB-07); no overlapping pending or approved leave (DB-08); a won deal has `won_at` and exactly one client (DB-09); hourly projects have a rate and currency (DB-10); rule runs are unique per rule and event and findings unique per fingerprint (DB-12); stream views and audit events cannot be rewritten (DB-13).

# 9. Live Employee Room

## 9.1 What the Room shows and what it never collects

| Collected in Release 1 | Never collected |
|---|---|
| Check-in and check-out time, current task the employee picks | Keystrokes, mouse movement, clipboard |
| Presence from `chrome.idle`: active, idle, locked (EV-003) | URLs, page titles, browsing history |
| Break kind and duration | Webcam, microphone, audio of any kind |
| Whether the screen is being shared (yes/no) | Screenshots, thumbnails, recordings |
| Live screen video while checked in, only to an authorized viewer, never stored | Anything while checked out or on break |

The Chrome Web Store prohibits collecting browsing activity except for a disclosed user-facing feature and requires prominent disclosure and affirmative consent (EV-009). The list above is the disclosure text's source; the extension's store listing, consent screen and privacy policy must say the same thing.

## 9.2 Consent

1.  On first sign-in the extension shows the monitoring notice (company policy topic `monitoring`, version from `organizations.room_policy_version`).
2.  The employee accepts (API-017). Without consent the employee can still check in for attendance; screen sharing never starts.
3.  When HR publishes a new monitoring policy, the version increases and every employee must accept again before the next share.
4.  An employee can withdraw consent at any time (`accept: false`); any active share stops at once.

## 9.3 Check-in, presence and breaks

| Step | Extension | Server |
|---|---|---|
| Check in | Popup "Check in" + optional task | API-018: opens `work_sessions` row (one open per employee, DB-06), computes `minutes_late`, issues extension token |
| Heartbeat | Every 30 s: `chrome.idle.queryState(300)` result, streaming yes/no, task | API-019: records state; writes a presence segment only on change |
| Offline | - | No heartbeat for 90 s -> `offline` (engine/presence.py, PRS-01) |
| Break | Break panel: kind and minutes | API-021: within the daily allowance the break starts at once; above it a manager decides (API-022); sharing pauses |
| Check out | Popup "Check out" + note | API-020: closes session, totals, `room` time entry for the task |

`chrome.idle` reports `active`, `idle` or `locked`; idle means no input for the detection interval (EV-003). EMS uses a 300-second interval, so a reader who does not touch the mouse for under 5 minutes stays active. Idle minutes are a review signal for a conversation, never an automatic deduction (Section 17).

## 9.4 Screen sharing (Media Session Page)

Chrome rules that shape this design (EV-001, EV-002, EV-008):

-   `getDisplayMedia()` needs a user gesture, and "the user must be prompted for permission every time"; permission cannot be persisted.
-   Chrome shows its own picker and sharing indicator. EMS cannot hide them, and must not try.
-   A content-script capture ends on navigation; an offscreen document (reasons `DISPLAY_MEDIA`, `WEB_RTC`, Chrome 109+, one open per extension) can hold media in the background.

Release 1 flow (DEC-006):

1.  After check-in, if `streaming_required` is true, the extension opens its own page `media.html` in a pinned tab: "Start screen sharing".
2.  The employee clicks; the page calls `navigator.mediaDevices.getDisplayMedia({video: {frameRate: 5}})` and Chrome shows the picker.
3.  The page calls API-024 for a publish token and publishes the track to LiveKit room `ems-<org_id>-<user_id>` with `livekit-client` 2.22.4.
4.  Heartbeats report `streaming: true`. If the employee stops sharing in Chrome's bar or closes the tab, the page reports `streaming: false` and the grid shows "Sharing stopped" - presence is unaffected.
5.  On break the page unpublishes the track; on break end it asks the employee to click "Resume sharing" (a new picker).

## 9.5 Viewing (CEO live grid and full-screen view)

-   The grid (API-025) shows presence, task and sharing state for everyone; no video until a viewer opens one person.
-   Opening a screen (API-026) requires `room.view_live` and a reason of 3 to 200 characters. EMS writes a `stream_views` row, sends the employee an in-extension notice "Imran Qureshi is viewing your screen", and returns a subscribe-only token for that employee's room (15 minutes, no publish, no data).
-   Closing the view (API-027) sets `ended_at`, the only column that can change (DB-13). Employees see every view of their own screen (API-028); no role can hide this.

## 9.6 Extension architecture (Manifest V3)

| Part | File (proposed) | Job |
|---|---|---|
| Manifest | extension/manifest.json | permissions: `idle`, `storage`, `alarms`; host permission for the EMS API origin only |
| Service worker | extension/src/background.ts | Sign-in token, 30-second `chrome.alarms` heartbeat, open Media Session Page |
| Popup | extension/src/popup/ | Sign-in, consent, check-in/out, task picker, break panel |
| Media Session Page | extension/src/media/ | `getDisplayMedia`, LiveKit publish, viewer notices |
| Settings | extension/src/settings/ | Company, notice text, "who viewed me" |

`chrome.alarms` has a minimum period; the heartbeat cadence must be confirmed against the Chrome alarms reference during TASK-011 (not yet inspected - Appendix G gap). If alarms cannot fire every 30 seconds, the Media Session Page (an open tab) sends heartbeats instead and the server's 90-second offline rule is unchanged.

::: callout-orange
OD-02 and OD-03 - decisions before live viewing of real employees

OD-02: monitoring of employees' screens is regulated differently by country and contract. Before `live_view_enabled` is switched on for any company, the product owner gets a legal review of the notice text, consent flow and retention for the pilot company's country (Pakistan, per fixture) and records it. OD-03: the extension is distributed either through the Chrome Web Store (public listing, store review against the policies in EV-009) or by force-install through the company's Chrome management. Development and the staff demo use an unpacked extension.
:::

# 10. People, Attendance and Leave

-   **Working day:** from `organizations.work_hours` (days, start, end, `late_grace_minutes`) in the company time zone; stored timestamps are UTC.
-   **Lateness:** `max(0, check_in_local - (start + grace))` in whole minutes on a working day.
-   **Status of a day:** `present` (session), `on_leave` (approved leave), `absent_unexplained` (working day, no session, no leave), `not_checked_in` (today, before end).
-   **Leave kinds:** annual, sick, casual, unpaid. Balances come from the published leave policy rules (for example `{"annual_days": 18, "casual_days": 8}`) minus approved working days in the calendar year.
-   **Overlap:** the database rejects overlapping pending or approved leave for the same employee (exclusion constraint, DB-08).
-   **Approver:** the manager if set; else HR; leadership roles go to the CEO.
-   **Daily report:** built at 23:30 company time from closed sessions (API-034).

# 11. HR Agent (rule-based)

The HR Agent is code in `engine/hr_agent.py` (21 engine tests pass, AGT-01..05). It classifies the question with ordered patterns, queries EMS records through a repository interface and answers in a fixed template with the IDs it used.

| Intent | Example question | Who may ask | Source |
|---|---|---|---|
| policy | "What is the attendance rule for late arrival?" | Everyone | hr_policies (quoted verbatim with version) |
| who_on_leave | "Who is on leave today?" | ceo, coo, hr, manager | leave_requests |
| pending_leave | "Which leave requests are pending?" | ceo, coo, hr, manager | leave_requests |
| late_arrivals | "Who came late today?" | ceo, coo, hr, manager | work_sessions |
| online_now | "Who is online now?" | ceo, coo, hr, manager | work_sessions |
| work_summary | "Work summary for Bilal yesterday" | Self; ceo, coo, hr, manager for others | presence_segments, time_entries |

Rules: policy patterns are checked first (so "late arrival rule" is a policy question, AGT-05); an unknown question returns `answered: false` with the list of supported questions; the agent never invents a person, number or policy; only the intent is logged (`agent_logs`), not the question text. The "reports to the CEO" part is the daily report (API-034) and the CEO dashboard's people tiles.

# 12. Projects, Tasks and Time

-   Board columns: `todo`, `active`, `review`, `done`. Allowed moves: todo<->active, active<->review, review->done, done->review.
-   Each move uses `expected_version`; the stale client gets 409 and reloads.
-   Room time: when an employee checks out (or switches task), active minutes on the selected task become one `room` time entry. Manual entries cannot overlap a Room session of the same person.
-   Billing types: fixed (budget), hourly (rate + currency), retainer, internal (no client).
-   Templates: `website_standard`, `mobile_app_standard` and `blank` are code constants in `backend/app/projects/templates.py` (12, 15 and 0 tasks); the Win action uses one.

# 13. CRM and Client Lifecycle

| Stage of the life cycle | Record | Moves when |
|---|---|---|
| Lead | contact `lifecycle_stage = lead` | Created manually, by import, or promoted from Lead Hunter |
| Qualified / opportunity | contact stage + deal `new`..`negotiation` | Deal created -> opportunity |
| Won | deal `won` + client `onboarding` + project | API-051 (one transaction; replay-safe, DB-09) |
| Active client | client `active` | First project task moves to active |
| At risk | client `at_risk` | Rule `invoice.overdue` > 30 days or no activity 30 days |
| Churned | client `churned` | Manual, with reason |

Stale deal: open stage and `last_activity_at` older than 14 days. Activities (API-052) reset the timer. Win always needs a company on the contact (`COMPANY_REQUIRED`).

# 14. Lead Hunter (own crawler)

## 14.1 Sourcing rules (DEC-010)

1.  Seeds are domains the user types or imports (max 200 per hunt). Blocked domains: linkedin.com, facebook.com, instagram.com, x.com, twitter.com, and Google or Bing search pages.
2.  Before any page: fetch `/robots.txt`. 4xx -> allowed; 5xx or network error -> do not crawl; parse at most 512,000 bytes (500 KiB); cache 24 hours; longest matching rule wins, allow wins a tie (RFC 9309, EV-011; engine/robots.py, ROB-01..03).
3.  User agent `EMS-LeadHunter/1.0 (+https://<deployment host>/bot)`; the `/bot` page explains the crawler and how to opt out.
4.  At most 5 pages per domain (home, about, services, contact, careers), 1 request per 5 seconds per domain, 10-second timeout, HTML only, 2 MB per page.
5.  Store only company name, public role addresses on the site (info@, sales@, contact@, hello@), detected technology tags, country hints, the source URL and the score. Do not store personal names, personal emails or phone numbers of individuals.
6.  Every domain is checked against `suppression_list` (SHA-256 of the normalized value) before crawling, promotion and drafting.

## 14.2 Scoring

Deterministic (engine/scoring.py, SCO-01): industry keyword 30, country 15, contact page 10, public email 15, team-size hint 15, technology 15; capped at 100; every point has a reason shown to the user.

## 14.3 Outreach

Drafts only (API-059): a template filled with signals, always with an opt-out line; the user copies it to their own mail client. Automatic sending and sequences wait for INT-003 and OD-05 (anti-spam law review for each target country).

# 15. Rule Engine (automation without API calls)

A rule is JSON with `trigger`, `when` (nested `all` / `any`, at most depth 3 and 20 conditions) and `then` (at most 5 actions). Operators: eq, neq, gt, gte, lt, lte, in, not_in, contains, is_empty. Actions: notify, create_task, assign_owner, set_stage_flag, create_finding, escalate. Each trigger allows a fixed list of facts (engine/rules.py `TRIGGER_FACTS`); anything else is rejected (`RULE_INVALID`, RUL-03). No code, regular expressions or URLs.

| Trigger | Fired by | Starter rule in Release 1 |
|---|---|---|
| deal.stale | Nightly job | `stale_deal_nudge`: notify owner + follow-up task after 14 days in proposal/negotiation |
| task.overdue | Hourly job | `overdue_billable_task`: notify project owner when a billable task is 24 h overdue |
| attendance.late | Check-in | `late_three_times`: notify HR when the same employee is late 3 times in 7 days |
| invoice.overdue | Nightly job | Mark client at risk after 30 days |
| leave.requested | Leave request | Notify approver; escalate to CEO if 2+ teammates already on leave |
| prospect.scored | Crawler | Notify hunt owner when score >= 80 |

Runs are recorded once per (rule, event) (DB-12). An action that emits another event carries a chain depth; at depth 3 the run is `skipped_loop`.

# 16. Graph Memory

EMS keeps a small company knowledge graph inside PostgreSQL so related information is found by traversal, not by an AI call.

| Edge | From -> to | Written when |
|---|---|---|
| works_on | person -> project / task | Task assigned |
| owns | person -> deal / project | Owner set |
| manages / reports_to | person -> person | Manager set |
| belongs_to | contact -> company | Contact saved |
| contact_of | contact -> client | Win |
| originated_from | project / client -> deal | Win |
| billed_by | project -> client; invoice -> client | Project or invoice saved |
| has_skill | person -> skill | Profile saved (Release 1: manual tags) |

`ems.graph_neighbors(node, depth)` walks current edges up to depth 3 under the caller's RLS (DB-11). Edges have `valid_from`/`valid_to`; a change closes the old edge and opens a new one, so history is kept. Uses: "Related" panels (API-047, API-068), the HR Agent's team lookups, and leakage evidence ("won deal -> client -> no project").

# 17. Revenue and Leakage Engine

Detectors run nightly at 01:00 company time in the worker (engine/leakage.py, LEK-01..06). Each finding has a kind, entity, amount at risk, currency, evidence and a fingerprint so it is created once (DB-12).

| Kind | Rule (defaults are company settings) | Amount at risk |
|---|---|---|
| unbilled_time | Billable time entries older than 7 days, not invoiced, on hourly projects | minutes / 60 x project hourly rate |
| overdue_invoice | Due date passed, outstanding > 0 | outstanding amount |
| stale_deal | Open stage, no activity for 14 days | deal amount x stage probability (new 0.10, qualified 0.25, proposal 0.50, negotiation 0.70) |
| won_without_project | Deal won 3+ days ago, no project | deal amount |
| won_without_invoice | Deal won 30+ days ago, no invoice | deal amount |
| over_budget | Fixed project cost >= 90% of budget | cost - budget (0 while still under) |
| idle_paid_time | Idle minutes in a day above 60 | idle minutes / 60 x member cost rate; evidence says "review with the employee before any action" |

`retainer_underused` is in the schema for Release 2 (no detector yet). Worked example from the fixture: 180 unbilled minutes at $40.00/h = $120.00; INV-2026-1031 overdue = $6,000.00; Contoso redesign $5,000.00 in proposal x 0.50 = $2,500.00; total $8,620.00 (API-065). Paying an invoice or logging an activity resolves the matching finding automatically on the next run.

# 18. Role Dashboards and KPI Sources

Every tile names its source. A tile with no EMS source appears in `unavailable` with a reason; it never shows sample numbers (AUD-04, AUD-05).

| Dashboard | Tiles with a Release 1 source | Unavailable in Release 1 |
|---|---|---|
| CEO | Checked in now, late today, on leave; open pipeline and weighted value; won this month; invoiced, collected, outstanding; revenue at risk; projects at risk | Profit, expenses |
| CTO | Engineering projects in progress; tasks done this week; overdue tasks; rule runs and failures; active automations | System uptime, open incidents, deployments, latency (need a monitoring/CI integration - Release 2) |
| CFO | Invoiced this month; collected; outstanding (all unpaid) with count; overdue (unpaid past due) with count; project budget use; revenue at risk | Operating expenses, net profit, payroll summary, bills |
| COO | Attendance rate; active projects; overdue tasks; pipeline by stage; open findings | Capacity planning |
| HR | Headcount; present, late, absent; pending leave; break overruns; idle above threshold | Payroll |
| Employee | My tasks by status; my time today; my leave balance; who viewed my screen this week | - |

Definitions that fix AUD-06 and AUD-07: outstanding = sum of (amount - payments) over invoices not paid or void; overdue = the same over invoices with `due_on` before today; overall budget ratio = sum of costs / sum of budgets, computed, never typed.

# 19. API Conventions

## 19.1 Envelope

Success: `{"success": true, "message"?: string, "data": {...}, "meta": {"api_version": "v1", "request_id", "timestamp"}}`. Error: `{"success": false, "error": {"code", "message", "retryable", "details"}, "meta": {"api_version", "request_id"}}`. Messages are written for the end user. `GET /health` and the Google redirects are the only responses outside the envelope.

## 19.2 Headers, pagination, time and money

-   `Idempotency-Key` (8 to 100 characters) on creating POSTs marked "required"; the stored response is replayed for 24 hours; same key with a different body -> 409 `IDEMPOTENCY_KEY_REUSED`.
-   `expected_version` in the body for updates of versioned rows; mismatch -> 409 `VERSION_CONFLICT` with `current_version`.
-   Cursor pagination: `limit` (default 25, max 100) and opaque `next_cursor`.
-   Timestamps are UTC ISO 8601 with `Z`; dates are company-local `YYYY-MM-DD`; amounts are decimal strings with a currency code.

## 19.3 Rate limits (PostgreSQL counters)

Login 10 per 15 minutes per email and IP; signup 5 per hour per IP; forgot password 3 per hour per email; HR Agent 30 per minute per user; heartbeats 4 per minute per session. Exceeding returns 429 `RATE_LIMITED` with `Retry-After`.

## 19.4 Synthetic fixture used by every example

All data is invented. Company "Acme Tech" (slug acme-tech, Asia/Karachi, PK, USD). People: Imran Qureshi (CEO), Sara Malik (CTO), Omar Siddiqui (CFO), Hina Shah (HR), Usman Tariq (manager, Engineering), Bilal Ahmed (employee, backend developer), Ayesha Noor (employee, design). Clients: Northwind Digital (won deal "Website rebuild", $5,000.00, project "Northwind website"), Contoso (hourly support project at $40.00/h; open deal "Contoso redesign"). Demo day Monday 12 October 2026; 09:02 PKT = 04:02 UTC. IDs are UUIDv5 values from a fixed namespace (`spec/gen_api.py`) so examples are reproducible. Email domains use `.example`.

# 20. AI Policy

1.  Release 1 makes no call to an external AI or language-model API (DEC-007). The automation dashboard shows the count of external API calls (0).
2.  Every automated decision is produced by code with a trace: rule traces (API-063), score reasons (API-057), HR Agent sources (API-035), leakage evidence (API-065).
3.  INT-006 (optional language-model adapter) is BLOCKED: interface `TextRephraser.rephrase(text, facts) -> text` may only reword an answer already computed, must be switchable off per company, must not receive names or emails, and requires a provider, cost limit and data agreement (OD-06) before it is built.
4.  No employee scoring: EMS reports facts (time, presence, tasks); it does not rank or rate people.
# 21. Release 1 Endpoint Registry - 70 HTTP Operations

| ID | Method | Path | Purpose | Auth |
|---------|--------|----------------------------------------------|------------------------------|-----------|
| API-001 | GET | /health | Health and readiness | public (private network for details) |
| API-002 | POST | /api/v1/auth/signup | Create company account | public |
| API-003 | POST | /api/v1/auth/login | Sign in with email and password | public |
| API-004 | POST | /api/v1/auth/logout | Sign out | session |
| API-005 | POST | /api/v1/auth/password/forgot | Request password reset | public |
| API-006 | POST | /api/v1/auth/password/reset | Reset password | public |
| API-007 | GET | /api/v1/auth/google/start | Start Google sign-in | public |
| API-008 | GET | /api/v1/auth/google/callback | Complete Google sign-in | public |
| API-009 | GET | /api/v1/me | Current user, companies and permissions | session |
| API-010 | PATCH | /api/v1/org | Company setup | session |
| API-011 | POST | /api/v1/invitations | Invite team members | session |
| API-012 | POST | /api/v1/invitations/accept | Accept invitation | session (new or existing user) |
| API-013 | GET | /api/v1/members | List members | session |
| API-014 | PATCH | /api/v1/members/{userId} | Update member role or details | session |
| API-015 | POST | /api/v1/members/{userId}/deactivate | Deactivate member | session |
| API-016 | GET | /api/v1/roles/permissions | Permissions matrix | session |
| API-017 | POST | /api/v1/room/consent | Record monitoring consent | session |
| API-018 | POST | /api/v1/room/check-in | Check in | session or extension |
| API-019 | POST | /api/v1/room/heartbeat | Presence heartbeat | extension |
| API-020 | POST | /api/v1/room/check-out | Check out | session or extension |
| API-021 | POST | /api/v1/room/breaks | Request break | session or extension |
| API-022 | POST | /api/v1/room/breaks/{breakId}/decision | Approve or reject break | session |
| API-023 | POST | /api/v1/room/breaks/{breakId}/end | End break | session or extension |
| API-024 | POST | /api/v1/room/stream/publish-token | Get screen-share publish token | extension |
| API-025 | GET | /api/v1/room/live | CEO live grid | session |
| API-026 | POST | /api/v1/room/stream/view | Open a live screen view | session |
| API-027 | POST | /api/v1/room/stream/view/{viewId}/end | Close a live view | session |
| API-028 | GET | /api/v1/room/my-viewers | Who viewed my screen | session or extension |
| API-029 | GET | /api/v1/employees | Employee directory | session |
| API-030 | GET | /api/v1/attendance | Attendance and timesheets | session |
| API-031 | POST | /api/v1/leave-requests | Request leave | session |
| API-032 | GET | /api/v1/leave-requests | List leave requests | session |
| API-033 | POST | /api/v1/leave-requests/{requestId}/decision | Approve or reject leave | session |
| API-034 | GET | /api/v1/hr/reports/daily | Daily and weekly HR report | session |
| API-035 | POST | /api/v1/hr-agent/ask | Ask the HR Agent | session |
| API-036 | GET | /api/v1/hr-agent/policies | List HR policies | session |
| API-037 | PUT | /api/v1/hr-agent/policies/{topic} | Publish HR policy | session |
| API-038 | GET | /api/v1/projects | Projects dashboard and list | session |
| API-039 | POST | /api/v1/projects | Create project | session |
| API-040 | GET | /api/v1/projects/{projectId}/board | Project details and Kanban | session |
| API-041 | POST | /api/v1/projects/{projectId}/tasks | Create task | session |
| API-042 | PATCH | /api/v1/tasks/{taskId} | Edit task | session |
| API-043 | POST | /api/v1/tasks/{taskId}/move | Move task on the board | session |
| API-044 | POST | /api/v1/tasks/{taskId}/time-entries | Log time manually | session |
| API-045 | POST | /api/v1/contacts | Create contact or lead | session |
| API-046 | POST | /api/v1/contacts/search | Search contacts | session |
| API-047 | GET | /api/v1/contacts/{contactId} | Contact and lead details | session |
| API-048 | POST | /api/v1/deals | Create deal | session |
| API-049 | GET | /api/v1/deals/pipeline | Sales pipeline board | session |
| API-050 | POST | /api/v1/deals/{dealId}/stage | Move deal stage | session |
| API-051 | POST | /api/v1/deals/{dealId}/win | Win deal and start client lifecycle | session |
| API-052 | POST | /api/v1/activities | Log activity | session |
| API-053 | POST | /api/v1/invoices | Record invoice | session |
| API-054 | POST | /api/v1/invoices/{invoiceId}/payments | Record payment | session |
| API-055 | POST | /api/v1/hunts | Start a hunt | session |
| API-056 | GET | /api/v1/hunts/{huntId} | Hunt status | session |
| API-057 | GET | /api/v1/hunts/{huntId}/prospects | Results and scoring | session |
| API-058 | POST | /api/v1/prospects/{prospectId}/promote | Promote prospect to CRM | session |
| API-059 | POST | /api/v1/prospects/{prospectId}/outreach-draft | Draft outreach email | session |
| API-060 | POST | /api/v1/suppressions | Add to do-not-contact list | session |
| API-061 | GET | /api/v1/rules | Automation dashboard | session |
| API-062 | POST | /api/v1/rules | Create rule | session |
| API-063 | POST | /api/v1/rules/{ruleId}/simulate | Simulate rule | session |
| API-064 | GET | /api/v1/rule-runs | Workflow execution logs | session |
| API-065 | GET | /api/v1/leakage/findings | Revenue leakage findings | session |
| API-066 | POST | /api/v1/leakage/findings/{findingId}/resolve | Resolve or dismiss finding | session |
| API-067 | GET | /api/v1/dashboards/{role} | Role-based dashboard | session |
| API-068 | GET | /api/v1/graph/neighbors | Graph memory: related items | session |
| API-069 | GET | /api/v1/notifications | Notifications | session |
| API-070 | POST | /api/v1/notifications/{notificationId}/read | Mark notification read | session |

::: callout-red
Endpoint result rule

Every operation shows its request (when it has a body), its success result and at least one error result in the exact envelope the API returns. All people, companies, IDs and amounts are synthetic (fixture in Section 19.4). Frontend and QA work from these examples; an endpoint is not done until its live responses match them in shape, status code and error code.
:::

# 22. System and Authentication Endpoint Contracts

## API-001 Health and readiness

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /health |
| Purpose | Load balancer readiness; 200 when PostgreSQL is reachable, body reports degraded dependencies. |
| Auth | public (private network for details) |
| Permission | None |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "status": "ready",
      "checks": {
        "postgres": "ok",
        "livekit": "ok",
        "worker_lag_seconds": 2
      },
      "version": "1.0.0"
    }

Degraded but serving (media server down) (200)

    {
      "status": "degraded",
      "checks": {
        "postgres": "ok",
        "livekit": "unavailable",
        "worker_lag_seconds": 3
      },
      "version": "1.0.0"
    }

Error result (503)

    {
      "status": "unavailable",
      "checks": {
        "postgres": "unavailable"
      },
      "version": "1.0.0"
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Ready or degraded |
| 503 | PostgreSQL unreachable |

-   Live streaming outage never removes API instances; the Room shows streams as unavailable and keeps presence working.

## API-002 Create company account

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/auth/signup |
| Purpose | Screen 'Create Company Account': creates the user, the company and the CEO membership in one transaction, then signs in. |
| Auth | public |
| Permission | Public; rate limited 5 per hour per IP |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required (client-generated UUID). |
| Audit | org.created, user.created |
| Domain event | org.created |
| Worker / async | Verification email (INT-003; until then the account is usable and the banner asks to verify). |

Request example

    {
      "company_name": "Acme Tech",
      "company_slug": "acme-tech",
      "country": "PK",
      "time_zone": "Asia/Karachi",
      "name": "Imran Qureshi",
      "email": "imran@acmetech.example",
      "password": "correct-horse-battery-staple-42"
    }

Success result (201)

    {
      "success": true,
      "message": "Company account created.",
      "data": {
        "user": {
          "id": "218ddf51-b83b-5f00-9e99-5e32103a1023",
          "name": "Imran Qureshi",
          "email": "imran@acmetech.example"
        },
        "org": {
          "id": "0f8c3a50-4105-5319-b2b1-b252e9c20343",
          "name": "Acme Tech",
          "slug": "acme-tech",
          "setup_state": "account_created"
        },
        "membership": {
          "role": "ceo"
        },
        "next_step": "company_setup"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-01T05:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "SLUG_TAKEN",
        "message": "That company address is already taken. Try another.",
        "retryable": false,
        "details": {
          "field": "company_slug"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created and signed in (Set-Cookie) |
| 400 | VALIDATION_FAILED - weak password (< 12 chars) or bad email |
| 409 | SLUG_TAKEN or EMAIL_IN_USE |
| 429 | RATE_LIMITED |

-   Password: 12-128 characters, checked against a local list of common passwords; stored as argon2id (argon2-cffi 25.1.0).

-   Uses `ems.signup_company()` because no organization context exists yet (verified, DB-03/DB-05).

## API-003 Sign in with email and password

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/auth/login |
| Purpose | Screen 01 Login: verify credentials and create a session; 'Keep me signed in' extends it to 30 days. |
| Auth | public |
| Permission | Public; 10 attempts per 15 min per email + IP |
| Path / query parameters | None |
| Idempotency / concurrency | Not idempotent; each success creates a session. |
| Audit | auth.login_succeeded / auth.login_failed (no password) |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "email": "imran@acmetech.example",
      "password": "correct-horse-battery-staple-42",
      "remember": true
    }

Success result (200)

    {
      "success": true,
      "message": "Signed in.",
      "data": {
        "user": {
          "id": "218ddf51-b83b-5f00-9e99-5e32103a1023",
          "name": "Imran Qureshi"
        },
        "session_expires_at": "2026-11-11T04:00:00Z",
        "organizations": [
          {
            "id": "0f8c3a50-4105-5319-b2b1-b252e9c20343",
            "name": "Acme Tech",
            "role": "ceo"
          }
        ],
        "redirect": "/dashboards/ceo"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "INVALID_CREDENTIALS",
        "message": "Email or password is incorrect.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Signed in (Set-Cookie ems_session) |
| 401 | INVALID_CREDENTIALS (same message for unknown email) |
| 429 | RATE_LIMITED |

-   Session token: 32 random bytes; only its SHA-256 is stored (`ems.create_session`).

-   Unknown email and wrong password return the same error and take similar time (dummy argon2 verify).

## API-004 Sign out

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/auth/logout |
| Purpose | Revoke the current session. |
| Auth | session |
| Permission | Signed-in user |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotent. |
| Audit | auth.logout |
| Domain event | None. |
| Worker / async | None. |

Request example

    {}

Success result (200)

    {
      "success": true,
      "data": {
        "signed_out": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T13:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "You are not signed in.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Signed out (cookie cleared) |
| 401 | No session |

-   Revocation is immediate (`ems.revoke_session`, DB-04).

## API-005 Request password reset

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/auth/password/forgot |
| Purpose | Send a reset link if the email exists; the response never reveals whether it does. |
| Auth | public |
| Permission | Public; 3 per hour per email |
| Path / query parameters | None |
| Idempotency / concurrency | Repeated requests replace the previous token. |
| Audit | auth.reset_requested |
| Domain event | None. |
| Worker / async | Reset email (INT-003). |

Request example

    {
      "email": "imran@acmetech.example"
    }

Success result (202)

    {
      "success": true,
      "message": "If that email has an account, a reset link is on its way.",
      "data": {
        "accepted": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:00:00Z"
      }
    }

Error result (429)

    {
      "success": false,
      "error": {
        "code": "RATE_LIMITED",
        "message": "Too many requests. Try again later.",
        "retryable": true,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 202 | Accepted (always, for known and unknown emails) |
| 429 | RATE_LIMITED |

-   Token valid 30 minutes, single use, stored hashed. Blocked until INT-003 email is available; the UI shows 'Contact your company admin' meanwhile.

## API-006 Reset password

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/auth/password/reset |
| Purpose | Set a new password with a reset token; revokes all existing sessions. |
| Auth | public |
| Permission | Valid reset token |
| Path / query parameters | None |
| Idempotency / concurrency | Token single-use. |
| Audit | auth.password_reset |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "token": "rst_redacted_example",
      "new_password": "a-new-long-passphrase-2026"
    }

Success result (200)

    {
      "success": true,
      "message": "Password changed. Sign in again.",
      "data": {
        "password_changed": true,
        "sessions_revoked": 2
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:10:00Z"
      }
    }

Error result (410)

    {
      "success": false,
      "error": {
        "code": "RESET_TOKEN_EXPIRED",
        "message": "This reset link has expired. Request a new one.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Changed |
| 400 | VALIDATION_FAILED - weak password |
| 410 | RESET_TOKEN_EXPIRED or already used |

-   All sessions of the user are revoked in the same transaction.

## API-007 Start Google sign-in

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/auth/google/start |
| Purpose | 'Continue with Google': redirect to Google's authorization endpoint with state and nonce. |
| Auth | public |
| Permission | Public |
| Path / query parameters | return_to (relative path, optional) |
| Idempotency / concurrency | Each call creates a new state value. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (302)

    {
      "status": 302,
      "location": "https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id=<GOOGLE_CLIENT_ID>&scope=openid%20email%20profile&redirect_uri=https%3A%2F%2Fapp.ems.example%2Fapi%2Fv1%2Fauth%2Fgoogle%2Fcallback&state=<random>&nonce=<random>&code_challenge=<S256>&code_challenge_method=S256",
      "set_cookie": "ems_oauth=<signed state+nonce+verifier>; HttpOnly; Secure; SameSite=Lax; Max-Age=600"
    }

Error result (503)

    {
      "success": false,
      "error": {
        "code": "GOOGLE_NOT_CONFIGURED",
        "message": "Google sign-in is not available. Use email and password.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 302 | Redirect to Google |
| 503 | GOOGLE_NOT_CONFIGURED |

-   Endpoints come from https://accounts.google.com/.well-known/openid-configuration (EV-006), cached per HTTP headers.

-   INTEGRATION STATUS: READY TO IMPLEMENT (documented); sandbox test in TASK-004 needs the Google OAuth client (OD-07).

## API-008 Complete Google sign-in

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/auth/google/callback |
| Purpose | Exchange the code, validate the ID token, then sign in an existing user or attach Google to a matching invited email. |
| Auth | public |
| Permission | Valid state cookie |
| Path / query parameters | code, state (query, from Google) |
| Idempotency / concurrency | Code is single-use at Google. |
| Audit | auth.login_succeeded (method google) |
| Domain event | None. |
| Worker / async | None. |

Success result (302)

    {
      "status": 302,
      "location": "/dashboards/ceo",
      "set_cookie": "ems_session=<token>; HttpOnly; Secure; SameSite=Lax"
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "GOOGLE_ACCOUNT_NOT_LINKED",
        "message": "No EMS account uses this Google account. Ask your company admin for an invitation.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 302 | Signed in, redirect |
| 400 | STATE_MISMATCH |
| 403 | GOOGLE_ACCOUNT_NOT_LINKED |

-   Validate signature (jwks_uri), iss in {https://accounts.google.com, accounts.google.com}, aud = client ID, exp, nonce; identify users by `sub`, never by email (EV-006).

-   Link Google to an existing user only when `email_verified` is true and the email matches a pending invitation or the signed-in user.

## API-009 Current user, companies and permissions

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/me |
| Purpose | Drives navigation: role, permissions and setup state. |
| Auth | session |
| Permission | Signed-in user |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "user": {
          "id": "218ddf51-b83b-5f00-9e99-5e32103a1023",
          "name": "Imran Qureshi",
          "email": "imran@acmetech.example"
        },
        "active_org": {
          "id": "0f8c3a50-4105-5319-b2b1-b252e9c20343",
          "name": "Acme Tech",
          "role": "ceo",
          "time_zone": "Asia/Karachi",
          "setup_state": "active"
        },
        "permissions": [
          "room.view_live",
          "room.self",
          "hr.manage",
          "leave.decide",
          "projects.manage",
          "crm.manage",
          "finance.manage",
          "hunter.use",
          "rules.manage",
          "members.manage",
          "leakage.read",
          "leakage.resolve",
          "dashboards.all"
        ],
        "dashboard": "ceo"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:00:05Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | No or expired session |

-   Permissions come from the role matrix (Section 7.2); the UI hides what is not listed, the API enforces it.

# 23. Company and Team Endpoint Contracts

## API-010 Company setup

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | PATCH |
| Path | /api/v1/org |
| Purpose | Screen 'Company Setup': industry, size, time zone, working hours. |
| Auth | session |
| Permission | members.manage (CEO, HR) |
| Path / query parameters | None |
| Idempotency / concurrency | expected_version required. |
| Audit | org.updated (field names) |
| Domain event | org.updated |
| Worker / async | None. |

Request example

    {
      "expected_version": 1,
      "industry": "Software services",
      "size_band": "11-50",
      "time_zone": "Asia/Karachi",
      "work_hours": {
        "days": [
          "mon",
          "tue",
          "wed",
          "thu",
          "fri"
        ],
        "start": "09:00",
        "end": "18:00",
        "late_grace_minutes": 10
      }
    }

Success result (200)

    {
      "success": true,
      "message": "Company details saved.",
      "data": {
        "id": "0f8c3a50-4105-5319-b2b1-b252e9c20343",
        "setup_state": "company_setup_done",
        "version": 2,
        "next_step": "invite_team"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-01T05:05:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "VERSION_CONFLICT",
        "message": "Company settings were changed by someone else. Reload and try again.",
        "retryable": false,
        "details": {
          "current_version": 2
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Saved |
| 400 | VALIDATION_FAILED |
| 403 | AUTHORIZATION_DENIED |
| 409 | VERSION_CONFLICT |

-   Working hours drive lateness and attendance (Section 10).

-   Invite screen 'Skip for now' and the first accepted invitation both set `setup_state` to `active` (send `{"expected_version": n, "setup_state": "active"}`).

## API-011 Invite team members

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/invitations |
| Purpose | Screen 06 Invite: up to 20 emails with roles and an optional message (max 300 characters). |
| Auth | session |
| Permission | members.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required; an email with a pending invitation is returned as `already_invited`. |
| Audit | member.invited |
| Domain event | member.invited |
| Worker / async | Invitation email (INT-003); until then the response includes copyable links for the inviter. |

Request example

    {
      "invites": [
        {
          "email": "bilal@acmetech.example",
          "role": "employee"
        },
        {
          "email": "hina@acmetech.example",
          "role": "hr"
        }
      ],
      "message": "Hi! Join our company workspace on EMS to collaborate with the team."
    }

Success result (201)

    {
      "success": true,
      "message": "2 invitations created.",
      "data": {
        "results": [
          {
            "email": "bilal@acmetech.example",
            "status": "invited",
            "invitation_id": "94ffbb52-3771-5b03-990c-2084c00093c3",
            "expires_at": "2026-10-08T05:10:00Z"
          },
          {
            "email": "hina@acmetech.example",
            "status": "invited",
            "invitation_id": "455e9bb7-b8ae-5432-a822-841a15291ca7",
            "expires_at": "2026-10-08T05:10:00Z"
          }
        ],
        "email_delivery": "not_configured",
        "copy_links": true,
        "org_setup_state": "team_invited"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-01T05:10:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Check the highlighted rows.",
        "retryable": false,
        "details": {
          "fields": {
            "invites[1].role": "Role 'ceo' cannot be invited; there is one CEO per company."
          }
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created (per-row results) |
| 400 | VALIDATION_FAILED |
| 403 | AUTHORIZATION_DENIED |

-   Allowed invite roles: cto, cfo, coo, hr, manager, employee (schema CHECK). The design's role list (Employee, HR, Manager) is a subset.

-   Tokens: 32 random bytes, stored hashed, valid 7 days, single use.

## API-012 Accept invitation

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/invitations/accept |
| Purpose | Join a company. New users set name and password in the same call. |
| Auth | session (new or existing user) |
| Permission | Holder of the token whose email matches |
| Path / query parameters | None |
| Idempotency / concurrency | Token single-use (DB-05). |
| Audit | member.joined |
| Domain event | member.joined |
| Worker / async | None. |

Request example

    {
      "token": "inv_redacted_example",
      "name": "Bilal Ahmed",
      "password": "bilal-long-passphrase-01"
    }

Success result (200)

    {
      "success": true,
      "message": "Welcome to Acme Tech.",
      "data": {
        "org": {
          "id": "0f8c3a50-4105-5319-b2b1-b252e9c20343",
          "name": "Acme Tech"
        },
        "membership": {
          "role": "employee"
        },
        "next_step": "install_extension"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-02T06:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "INVITATION_EMAIL_MISMATCH",
        "message": "This invitation was sent to a different email address.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Joined |
| 403 | INVITATION_EMAIL_MISMATCH |
| 410 | INVITATION_INVALID (expired, used or revoked) |

-   Implemented by `ems.accept_invitation()` (DB-05).

## API-013 List members

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/members |
| Purpose | Directory used by HR, assignment pickers and the Room. |
| Auth | session |
| Permission | Any member (cost rates only for finance.manage) |
| Path / query parameters | role, status, department, cursor, limit |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "user_id": "218ddf51-b83b-5f00-9e99-5e32103a1023",
            "name": "Imran Qureshi",
            "role": "ceo",
            "title": "Chief Executive",
            "department": "Leadership",
            "status": "active"
          },
          {
            "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
            "name": "Bilal Ahmed",
            "role": "employee",
            "title": "Backend Developer",
            "department": "Engineering",
            "status": "active",
            "manager_id": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f"
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:05:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   `cost_rate` is included only for CEO and CFO.

## API-014 Update member role or details

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | PATCH |
| Path | /api/v1/members/{userId} |
| Purpose | Change role, title, department, manager or cost rate. |
| Auth | session |
| Permission | members.manage (cost_rate: finance.manage) |
| Path / query parameters | userId |
| Idempotency / concurrency | expected_version required. |
| Audit | member.updated (fields) |
| Domain event | member.role_changed |
| Worker / async | Graph edge reports_to updated. |

Request example

    {
      "expected_version": 1,
      "role": "manager",
      "department": "Engineering"
    }

Success result (200)

    {
      "success": true,
      "message": "Member updated.",
      "data": {
        "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
        "role": "manager",
        "department": "Engineering",
        "version": 2
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "ONE_CEO_ONLY",
        "message": "A company has exactly one CEO. Transfer the CEO role from the CEO's own settings.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Updated |
| 403 | AUTHORIZATION_DENIED |
| 404 | NOT_FOUND |
| 409 | VERSION_CONFLICT |
| 422 | ONE_CEO_ONLY (DB-07) |

-   Role change takes effect on the next request.

## API-015 Deactivate member

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/members/{userId}/deactivate |
| Purpose | Remove access; open tasks and deals are reassigned; open work session is closed. |
| Auth | session |
| Permission | members.manage |
| Path / query parameters | userId |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | member.deactivated |
| Domain event | member.deactivated |
| Worker / async | Close live stream; revoke extension tokens. |

Request example

    {
      "reassign_to": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f",
      "reason": "Contract ended"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
        "status": "deactivated",
        "tasks_reassigned": 6,
        "deals_reassigned": 0,
        "work_session_closed": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T12:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "CANNOT_DEACTIVATE_CEO",
        "message": "The CEO cannot be deactivated.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Deactivated |
| 403 | AUTHORIZATION_DENIED |
| 404 | NOT_FOUND |
| 422 | CANNOT_DEACTIVATE_CEO |

-   History stays; the person appears as 'Former member' in records.

## API-016 Permissions matrix

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/roles/permissions |
| Purpose | Screen 'Permissions Matrix' (read-only in Release 1; custom roles are Release 2). |
| Auth | session |
| Permission | Any member |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "roles": [
          "ceo",
          "cto",
          "cfo",
          "coo",
          "hr",
          "manager",
          "employee"
        ],
        "matrix": {
          "room.view_live": [
            "ceo",
            "coo"
          ],
          "hr.manage": [
            "ceo",
            "coo",
            "hr"
          ],
          "leave.decide": [
            "ceo",
            "hr",
            "manager"
          ],
          "finance.manage": [
            "ceo",
            "cfo"
          ],
          "crm.manage": [
            "ceo",
            "coo",
            "manager"
          ],
          "rules.manage": [
            "ceo",
            "coo",
            "cto"
          ]
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:05:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   The full matrix is in Section 7.2; this endpoint returns the same data.

# 24. Live Employee Room Endpoint Contracts

## API-017 Record monitoring consent

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/consent |
| Purpose | Extension screen 'First-Install Consent': the employee reads the monitoring notice and accepts the current policy version. |
| Auth | session |
| Permission | room.self (any member) |
| Path / query parameters | None |
| Idempotency / concurrency | Repeat for the same version returns the existing consent. |
| Audit | room.consent_given / room.consent_revoked |
| Domain event | room.consent_changed |
| Worker / async | None. |

Request example

    {
      "policy_version": 1,
      "accept": true
    }

Success result (200)

    {
      "success": true,
      "message": "Consent recorded.",
      "data": {
        "policy_version": 1,
        "consented_at": "2026-10-02T06:05:00Z",
        "covers": [
          "presence",
          "idle_state",
          "current_task",
          "live_screen_while_checked_in"
        ],
        "excludes": [
          "recording",
          "keystrokes",
          "browsing_history",
          "webcam",
          "microphone"
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-02T06:05:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "POLICY_VERSION_OUTDATED",
        "message": "A newer monitoring notice exists. Read version 2 before accepting.",
        "retryable": false,
        "details": {
          "current_version": 2
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Recorded |
| 409 | POLICY_VERSION_OUTDATED |

-   Without current consent, check-in still works for attendance but the extension never starts screen sharing (OD-02 legal review).

-   `accept: false` revokes consent and stops any active stream immediately.

## API-018 Check in

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/check-in |
| Purpose | Extension 'Check-in' popup: opens the work session; returns an extension token and whether streaming is expected. |
| Auth | session or extension |
| Permission | room.self |
| Path / query parameters | None |
| Idempotency / concurrency | One open session per employee (DB-06); a repeat returns the open session. |
| Audit | room.checked_in |
| Domain event | room.checked_in |
| Worker / async | Lateness rule (attendance.late). |

Request example

    {
      "device": {
        "kind": "chrome_extension",
        "extension_version": "1.0.0"
      },
      "task_id": "ab69355b-311b-59bc-b64e-306dd5c5b308"
    }

Success result (201)

    {
      "success": true,
      "message": "Checked in at 9:02 AM.",
      "data": {
        "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
        "started_at": "2026-10-12T04:02:00Z",
        "minutes_late": 0,
        "presence": "active",
        "extension_token": "ext_redacted_example",
        "heartbeat_seconds": 30,
        "streaming_required": true,
        "next": "start_screen_share"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:02:00Z"
      }
    }

Repeat check-in while a session is open (200)

    {
      "success": true,
      "data": {
        "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
        "started_at": "2026-10-12T04:02:00Z",
        "presence": "active",
        "already_open": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:05:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "ON_APPROVED_LEAVE",
        "message": "You are on approved leave today. Ask HR to cancel the leave before checking in.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Session opened |
| 200 | Already checked in |
| 403 | ON_APPROVED_LEAVE |
| 423 | MEMBER_DEACTIVATED |

-   Lateness = start minus (work start + grace) in the company time zone; 0 when on time.

-   `streaming_required` is true only when the company enabled live view and the employee consented (API-017).

## API-019 Presence heartbeat

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/heartbeat |
| Purpose | Every 30 s from the extension: chrome.idle state, stream state, current task. |
| Auth | extension |
| Permission | Owner of the open session |
| Path / query parameters | None |
| Idempotency / concurrency | Heartbeats are idempotent by (session_id, sent_at). |
| Audit | None (high volume). |
| Domain event | room.presence_changed (only on change) |
| Worker / async | Segments written on state change. |

Request example

    {
      "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
      "sent_at": "2026-10-12T05:30:00Z",
      "idle_state": "active",
      "streaming": true,
      "task_id": "ab69355b-311b-59bc-b64e-306dd5c5b308"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "presence": "active",
        "server_time": "2026-10-12T05:30:01Z",
        "next_heartbeat_seconds": 30,
        "pending_break_decision": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T05:30:01Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "SESSION_CLOSED",
        "message": "Your work session has ended. Check in again to continue.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Accepted |
| 401 | Extension token invalid |
| 409 | SESSION_CLOSED |

-   Server derives presence (engine/presence.py, PRS-01..02): no heartbeat for 90 s = offline.

-   The extension sends no URLs, page titles, keystrokes or screenshots.

## API-020 Check out

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/check-out |
| Purpose | Close the work session; stream stops; daily totals computed. |
| Auth | session or extension |
| Permission | room.self |
| Path / query parameters | None |
| Idempotency / concurrency | Repeat returns the closed session. |
| Audit | room.checked_out |
| Domain event | room.checked_out |
| Worker / async | Daily summary for HR Agent; idle_paid_time detector input. |

Request example

    {
      "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
      "note": "Auth API done, starting tests tomorrow"
    }

Success result (200)

    {
      "success": true,
      "message": "Checked out. Good work today.",
      "data": {
        "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
        "started_at": "2026-10-12T04:02:00Z",
        "ended_at": "2026-10-12T13:05:00Z",
        "totals_minutes": {
          "active": 412,
          "idle": 38,
          "on_break": 45,
          "offline": 48
        },
        "time_entries_created": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T13:05:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "NO_OPEN_SESSION",
        "message": "You are not checked in.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Closed |
| 409 | NO_OPEN_SESSION |

-   Sessions still open 2 hours after work end are auto-closed at the last heartbeat (`auto_closed`).

-   Active minutes on a task become a `room` time entry for that task.

## API-021 Request break

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/breaks |
| Purpose | Extension 'Break Request Panel'. |
| Auth | session or extension |
| Permission | room.self |
| Path / query parameters | None |
| Idempotency / concurrency | One active break per employee (unique index). |
| Audit | room.break_requested |
| Domain event | room.break_requested |
| Worker / async | Notify manager when approval is required. |

Request example

    {
      "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4",
      "kind": "lunch",
      "minutes": 45
    }

Success result (201)

    {
      "success": true,
      "message": "Lunch break started. Screen sharing paused.",
      "data": {
        "break_id": "05f3ce82-b1a0-5c37-8eff-2fc66eb26688",
        "status": "active",
        "started_at": "2026-10-12T08:00:00Z",
        "approval": "auto_approved_by_policy",
        "stream_paused": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T08:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "BREAK_ALREADY_ACTIVE",
        "message": "You already have an active break.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Started or requested |
| 409 | BREAK_ALREADY_ACTIVE / NO_OPEN_SESSION |

-   Policy (company setting): breaks up to the daily allowance start immediately; longer requests wait for a manager decision (API-022).

-   Screen sharing pauses during breaks.

## API-022 Approve or reject break

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/breaks/{breakId}/decision |
| Purpose | Manager decides a break above the allowance. |
| Auth | session |
| Permission | leave.decide for the employee's team |
| Path / query parameters | breakId |
| Idempotency / concurrency | First decision wins; later decisions return 409. |
| Audit | room.break_decided |
| Domain event | room.break_decided |
| Worker / async | Notify employee. |

Request example

    {
      "decision": "approved"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "break_id": "d59a0b41-7ef1-5c69-8f5e-44839c2df18c",
        "status": "active",
        "started_at": "2026-10-12T10:00:00Z",
        "decided_by": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T10:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "ALREADY_DECIDED",
        "message": "This break request was already decided.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Decided |
| 403 | AUTHORIZATION_DENIED |
| 409 | ALREADY_DECIDED |

-   Rejected requests leave the employee in active presence.

## API-023 End break

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/breaks/{breakId}/end |
| Purpose | Return from break; streaming resumes if consented. |
| Auth | session or extension |
| Permission | Break owner |
| Path / query parameters | breakId |
| Idempotency / concurrency | Repeat returns the ended break. |
| Audit | room.break_ended |
| Domain event | room.break_ended |
| Worker / async | None. |

Request example

    {}

Success result (200)

    {
      "success": true,
      "data": {
        "break_id": "05f3ce82-b1a0-5c37-8eff-2fc66eb26688",
        "status": "ended",
        "minutes": 45,
        "over_allowance_minutes": 0,
        "stream_resume": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T08:45:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Break not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Ended |
| 404 | NOT_FOUND |

-   Over-allowance minutes are reported to HR, not deducted automatically.

## API-024 Get screen-share publish token

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/stream/publish-token |
| Purpose | The extension offscreen document gets a LiveKit token to publish the employee's screen to the company room. |
| Auth | extension |
| Permission | Checked in, consented, not on break |
| Path / query parameters | None |
| Idempotency / concurrency | New short-lived token each call. |
| Audit | room.stream_started |
| Domain event | room.stream_state |
| Worker / async | None. |

Request example

    {
      "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "livekit_url": "wss://media.ems.example",
        "token": "eyJ...redacted",
        "room": "ems-0f8c3a50-4105-5319-b2b1-b252e9c20343-289b359a-7306-54e2-a6c2-1346e443935a",
        "identity": "employee:289b359a-7306-54e2-a6c2-1346e443935a",
        "grants": {
          "can_publish": true,
          "can_subscribe": false,
          "can_publish_data": false,
          "can_publish_sources": [
            "screen_share"
          ]
        },
        "expires_in_seconds": 600,
        "video": {
          "max_resolution": "1280x720",
          "max_fps": 5
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T04:02:30Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "CONSENT_REQUIRED",
        "message": "Accept the monitoring notice before sharing your screen.",
        "retryable": false,
        "details": {
          "policy_version": 1
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Token issued |
| 403 | CONSENT_REQUIRED / ON_BREAK |
| 409 | NO_OPEN_SESSION |
| 503 | MEDIA_UNAVAILABLE |

-   Token built with livekit-api 1.2.1 `AccessToken(key, secret).with_identity(...).with_ttl(timedelta(seconds=600)).with_grants(VideoGrants(room_join=True, room=..., can_publish=True, can_subscribe=False, can_publish_data=False, can_publish_sources=['screen_share']))`; one LiveKit room per employee (locally checked, tools/check_livekit_tokens.py LK-01..03, EV-004).

-   Chrome requires the employee to pick the screen in the picker each time sharing starts; it cannot be started silently (EV-001).

## API-025 CEO live grid

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/room/live |
| Purpose | 'CEO Live Grid': everyone checked in, presence, current task, stream availability. |
| Auth | session |
| Permission | room.view_live (CEO, COO) |
| Path / query parameters | department, presence, cursor, limit (max 48) |
| Idempotency / concurrency | Read-only; refresh every 15 s or via server-sent events. |
| Audit | None (viewing a stream is audited by API-026). |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "as_of": "2026-10-12T05:30:05Z",
        "counts": {
          "checked_in": 12,
          "active": 9,
          "idle": 1,
          "on_break": 2,
          "offline": 0,
          "not_checked_in": 2,
          "on_leave": 1
        },
        "items": [
          {
            "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
            "name": "Bilal Ahmed",
            "department": "Engineering",
            "presence": "active",
            "since": "2026-10-12T04:02:00Z",
            "current_task": {
              "id": "ab69355b-311b-59bc-b64e-306dd5c5b308",
              "title": "Auth API"
            },
            "stream": "live",
            "minutes_late": 0
          },
          {
            "user_id": "6e857032-0821-59a4-9317-049c2b781524",
            "name": "Ayesha Noor",
            "department": "Design",
            "presence": "on_break",
            "since": "2026-10-12T05:20:00Z",
            "current_task": null,
            "stream": "paused",
            "minutes_late": 12
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T05:30:05Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "Only the CEO and COO can open the live room.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   Thumbnails are not stored; the grid shows the live track only when a viewer opens it (API-026).

## API-026 Open a live screen view

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/stream/view |
| Purpose | 'Full-Screen Monitoring': subscribe to one employee's screen; the view is logged and visible to that employee. |
| Auth | session |
| Permission | room.view_live |
| Path / query parameters | None |
| Idempotency / concurrency | Each call opens a new view record. |
| Audit | room.stream_viewed (viewer, subject, reason) |
| Domain event | room.view_started (employee is notified in the extension) |
| Worker / async | None. |

Request example

    {
      "subject_user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
      "reason": "Daily stand-up check"
    }

Success result (201)

    {
      "success": true,
      "data": {
        "view_id": "10068f45-9612-56fe-8474-19eefba55377",
        "livekit_url": "wss://media.ems.example",
        "token": "eyJ...redacted",
        "room": "ems-0f8c3a50-4105-5319-b2b1-b252e9c20343-289b359a-7306-54e2-a6c2-1346e443935a",
        "grants": {
          "can_publish": false,
          "can_subscribe": true,
          "can_publish_data": false
        },
        "expires_in_seconds": 900,
        "subject_notified": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T05:31:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "STREAM_NOT_LIVE",
        "message": "Bilal is not sharing right now (on break or not checked in).",
        "retryable": false,
        "details": {
          "presence": "on_break"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | View opened |
| 400 | VALIDATION_FAILED - reason required |
| 403 | AUTHORIZATION_DENIED |
| 409 | STREAM_NOT_LIVE |

-   A reason of 3-200 characters is required (stream_views CHECK).

-   Release 1 never records video; recording history is Release 2 and needs OD-02.

## API-027 Close a live view

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/room/stream/view/{viewId}/end |
| Purpose | End the view record when the viewer closes the stream. |
| Auth | session |
| Permission | The viewer |
| Path / query parameters | viewId |
| Idempotency / concurrency | Repeat returns the closed view. |
| Audit | room.stream_view_ended |
| Domain event | None. |
| Worker / async | Views open longer than the token lifetime are closed by the sweeper. |

Request example

    {}

Success result (200)

    {
      "success": true,
      "data": {
        "view_id": "10068f45-9612-56fe-8474-19eefba55377",
        "started_at": "2026-10-12T05:31:00Z",
        "ended_at": "2026-10-12T05:34:20Z",
        "seconds": 200
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T05:34:20Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "View not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Closed |
| 404 | NOT_FOUND |

-   Only `ended_at` can change on a view record (DB-13).

## API-028 Who viewed my screen

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/room/my-viewers |
| Purpose | Transparency: an employee sees every view of their screen with viewer, time and reason. |
| Auth | session or extension |
| Permission | room.self |
| Path / query parameters | from, to |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "view_id": "10068f45-9612-56fe-8474-19eefba55377",
            "viewer": "Imran Qureshi",
            "reason": "Daily stand-up check",
            "started_at": "2026-10-12T05:31:00Z",
            "seconds": 200
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   Cannot be disabled by any role.

# 25. People and HR Endpoint Contracts

## API-029 Employee directory

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/employees |
| Purpose | 'Employee Directory' with today's attendance state. |
| Auth | session |
| Permission | hr.manage, or manager for own team |
| Path / query parameters | department, status, q, cursor, limit |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
            "name": "Bilal Ahmed",
            "title": "Backend Developer",
            "department": "Engineering",
            "manager": "Usman Tariq",
            "today": {
              "state": "checked_in",
              "since": "2026-10-12T04:02:00Z",
              "minutes_late": 0
            },
            "leave_balance_days": {
              "annual": 14,
              "casual": 6
            }
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T05:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "You can only see your own profile.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   Leave balances are computed from policy and approved leave (Section 10).

## API-030 Attendance and timesheets

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/attendance |
| Purpose | 'Attendance and Timesheets': per-day totals from work sessions and presence segments. |
| Auth | session |
| Permission | hr.manage; employees see their own |
| Path / query parameters | user_id, from, to (dates, company time zone) |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "user_id": "289b359a-7306-54e2-a6c2-1346e443935a",
        "days": [
          {
            "date": "2026-10-12",
            "check_in": "09:02",
            "check_out": "18:05",
            "minutes_late": 0,
            "active": 412,
            "idle": 38,
            "on_break": 45,
            "offline": 48,
            "status": "present"
          },
          {
            "date": "2026-10-13",
            "status": "not_checked_in"
          }
        ],
        "totals": {
          "present_days": 1,
          "late_days": 0,
          "active_minutes": 412
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-13T06:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Choose a range of at most 62 days.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 400 | VALIDATION_FAILED |
| 403 | AUTHORIZATION_DENIED |

-   Times are shown in the company time zone; storage is UTC.

## API-031 Request leave

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/leave-requests |
| Purpose | 'Leave Request'. |
| Auth | session |
| Permission | Any member for self |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required; overlapping requests are rejected by the database (DB-08). |
| Audit | leave.requested |
| Domain event | leave.requested |
| Worker / async | leave.requested rules; notify approver. |

Request example

    {
      "kind": "annual",
      "start_date": "2026-10-20",
      "end_date": "2026-10-22",
      "reason": "Family event"
    }

Success result (201)

    {
      "success": true,
      "message": "Leave request sent to Imran Qureshi.",
      "data": {
        "request_id": "926408eb-ff9a-5b9b-9bb8-002245f807af",
        "status": "pending",
        "days": 3,
        "approver": "Imran Qureshi",
        "balance_after_approval": {
          "annual": 11
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "LEAVE_OVERLAP",
        "message": "You already have leave requested or approved for part of these dates.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Requested |
| 400 | VALIDATION_FAILED |
| 409 | LEAVE_OVERLAP |
| 422 | INSUFFICIENT_BALANCE |

-   Days count working days only (company calendar).

-   Approver: manager if set, else HR; CEO approves for leadership roles and when the company enables 'CEO Leave Approval'.

## API-032 List leave requests

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/leave-requests |
| Purpose | Approver queue and the employee's own history. |
| Auth | session |
| Permission | Own requests; approvers see their queue |
| Path / query parameters | status, scope (mine\|to_decide), cursor |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "request_id": "926408eb-ff9a-5b9b-9bb8-002245f807af",
            "employee": "Bilal Ahmed",
            "kind": "annual",
            "start_date": "2026-10-20",
            "end_date": "2026-10-22",
            "days": 3,
            "status": "pending",
            "team_on_leave_same_days": 1
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T07:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   `team_on_leave_same_days` helps approvers avoid staffing gaps.

## API-033 Approve or reject leave

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/leave-requests/{requestId}/decision |
| Purpose | 'CEO Leave Approval' and manager/HR approval. |
| Auth | session |
| Permission | leave.decide for this employee |
| Path / query parameters | requestId |
| Idempotency / concurrency | expected_version required; first decision wins. |
| Audit | leave.decided |
| Domain event | leave.decided |
| Worker / async | Notify employee; graph and attendance calendars updated. |

Request example

    {
      "expected_version": 1,
      "decision": "approved",
      "note": "Enjoy"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "request_id": "926408eb-ff9a-5b9b-9bb8-002245f807af",
        "status": "approved",
        "decided_by": "Imran Qureshi",
        "decided_at": "2026-10-12T07:05:00Z",
        "version": 2
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T07:05:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "VERSION_CONFLICT",
        "message": "This request was already decided.",
        "retryable": false,
        "details": {
          "current_status": "approved"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Decided |
| 403 | AUTHORIZATION_DENIED - cannot approve own leave |
| 409 | VERSION_CONFLICT |

-   Nobody can approve their own leave.

## API-034 Daily and weekly HR report

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/hr/reports/daily |
| Purpose | 'Daily/Weekly Reports': attendance, lateness, leave, idle above threshold, top tasks. |
| Auth | session |
| Permission | hr.manage |
| Path / query parameters | date or week (ISO week, e.g. 2026-W42) |
| Idempotency / concurrency | Read-only; built from closed sessions. |
| Audit | None. |
| Domain event | None. |
| Worker / async | Nightly pre-computation at 23:30 company time. |

Success result (200)

    {
      "success": true,
      "data": {
        "date": "2026-10-12",
        "headcount": 15,
        "present": 12,
        "on_leave": 1,
        "absent_unexplained": 2,
        "late": [
          {
            "name": "Ayesha Noor",
            "minutes": 12
          }
        ],
        "idle_over_threshold": [
          {
            "name": "Ayesha Noor",
            "idle_minutes": 74
          }
        ],
        "break_over_allowance": [],
        "active_minutes_total": 4380,
        "notes": "Idle time is a review signal, not a performance score."
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T19:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "Only HR and leadership can view company reports.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   Absent = no session, no approved leave, working day.

## API-035 Ask the HR Agent

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/hr-agent/ask |
| Purpose | 'HR Agent Query and Work Summary': rule-based answers from EMS records with sources; no language model. |
| Auth | session |
| Permission | Any member (scope limited by role) |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | agent_logs (intent only; the question text is not stored) |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "question": "Who is on leave today?"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "intent": "who_on_leave",
        "answered": true,
        "text": "1 on leave on 2026-10-12: Hina Shah (annual)",
        "data": [
          {
            "user_id": "f1827736-f757-56f9-b2ba-d20bf79ec95a",
            "name": "Hina Shah",
            "kind": "annual",
            "request_id": "bb220294-19f7-5f0d-9c48-e5193175adff"
          }
        ],
        "sources": [
          "bb220294-19f7-5f0d-9c48-e5193175adff"
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Question outside the agent's knowledge (never guessed) (200)

    {
      "success": true,
      "data": {
        "intent": "unknown",
        "answered": false,
        "text": "I can't answer that from EMS records. I can answer: Who is on leave today?; Which leave requests are pending?; Who came late today?; Who is online now?; Work summary for <name> yesterday; What is the leave policy?",
        "data": [],
        "sources": []
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Ask a question of 3 to 300 characters.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Answered or explained why not |
| 400 | VALIDATION_FAILED |

-   Implemented by engine/hr_agent.py (AGT-01..05). Employees cannot query other people's data.

## API-036 List HR policies

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/hr-agent/policies |
| Purpose | 'HR Agent Rules and Policies': published policies the agent quotes. |
| Auth | session |
| Permission | Any member |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "topic": "leave",
            "version": 2,
            "text": "18 annual days and 8 casual days per year. Requests 3+ days need 7 days' notice.",
            "published_at": "2026-10-01T06:00:00Z"
          },
          {
            "topic": "attendance",
            "version": 1,
            "text": "Work hours 09:00-18:00, 10 minutes grace. Lunch 45 minutes.",
            "published_at": "2026-10-01T06:00:00Z"
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   Policies are plain text written by HR; the agent quotes them verbatim with the version.

## API-037 Publish HR policy

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | PUT |
| Path | /api/v1/hr-agent/policies/{topic} |
| Purpose | HR publishes a new version of a policy and its machine rules (allowances, grace). |
| Auth | session |
| Permission | hr.manage |
| Path / query parameters | topic (leave\|attendance\|breaks\|general\|monitoring) |
| Idempotency / concurrency | expected_version required; creates version n+1. |
| Audit | policy.published |
| Domain event | policy.published |
| Worker / async | Rules referencing the policy reload. |

Request example

    {
      "expected_version": 1,
      "text": "Work hours 09:00-18:00, 15 minutes grace. Lunch 45 minutes.",
      "rules": {
        "late_grace_minutes": 15,
        "daily_break_allowance_minutes": 60
      }
    }

Success result (200)

    {
      "success": true,
      "message": "Attendance policy v2 published.",
      "data": {
        "topic": "attendance",
        "version": 2,
        "published_at": "2026-10-12T07:00:00Z"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T07:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "VERSION_CONFLICT",
        "message": "Someone published a newer version. Reload first.",
        "retryable": false,
        "details": {
          "current_version": 2
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Published |
| 403 | AUTHORIZATION_DENIED |
| 409 | VERSION_CONFLICT |

-   Changing the monitoring notice (room policy) also bumps the consent version (API-017).

# 26. Projects and Tasks Endpoint Contracts

## API-038 Projects dashboard and list

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/projects |
| Purpose | 'Projects Dashboard and List' with progress, budget burn and overdue counts. |
| Auth | session |
| Permission | Members see projects they are on; projects.manage sees all |
| Path / query parameters | status, client_id, cursor, limit |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "cb177fe3-6957-56c8-88b8-b33a4a0d61c3",
            "name": "Northwind website",
            "client": "Northwind Digital",
            "status": "active",
            "billing_type": "fixed",
            "progress_pct": 40,
            "tasks": {
              "todo": 6,
              "active": 3,
              "review": 1,
              "done": 7
            },
            "overdue": 1,
            "budget": {
              "amount": "5000.00",
              "cost_to_date": "1820.00",
              "currency": "USD",
              "ratio": "0.36"
            }
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   Budget figures appear only for finance.manage and project owners; cost uses member cost rates.

## API-039 Create project

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/projects |
| Purpose | Create a client or internal project. |
| Auth | session |
| Permission | projects.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | project.created |
| Domain event | project.created |
| Worker / async | Graph node + edges (client, owner). |

Request example

    {
      "name": "Contoso support",
      "client_id": "6cb07699-9f2f-5be6-822c-80e73d859c08",
      "billing_type": "hourly",
      "hourly_rate": "40.00",
      "currency": "USD",
      "owner_id": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f"
    }

Success result (201)

    {
      "success": true,
      "message": "Project created.",
      "data": {
        "id": "59cf8f13-d5aa-5fc6-a48b-96633950e42e",
        "name": "Contoso support",
        "status": "planned",
        "billing_type": "hourly",
        "version": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:10:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Hourly projects need an hourly rate and currency.",
        "retryable": false,
        "details": {
          "fields": {
            "hourly_rate": "Required for hourly billing."
          }
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created |
| 400 | VALIDATION_FAILED (DB-10 constraints) |
| 403 | AUTHORIZATION_DENIED |

-   Non-internal projects require a client.

## API-040 Project details and Kanban

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/projects/{projectId}/board |
| Purpose | 'Project Details and Kanban': columns To do, Active, Review, Done. |
| Auth | session |
| Permission | Project member or projects.manage |
| Path / query parameters | projectId, assignee_id |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "project": {
          "id": "cb177fe3-6957-56c8-88b8-b33a4a0d61c3",
          "name": "Northwind website",
          "client": "Northwind Digital"
        },
        "columns": {
          "todo": [
            {
              "id": "cf2a580b-afba-595c-bf03-0450564fbc0e",
              "title": "SEO audit",
              "assignee": "Ayesha Noor",
              "due_at": "2026-10-16T13:00:00Z",
              "position": 1,
              "version": 1
            }
          ],
          "active": [
            {
              "id": "ab69355b-311b-59bc-b64e-306dd5c5b308",
              "title": "Auth API",
              "assignee": "Bilal Ahmed",
              "due_at": "2026-10-12T13:00:00Z",
              "position": 1,
              "version": 3,
              "minutes_logged": 300
            }
          ],
          "review": [],
          "done": []
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Project not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 404 | NOT_FOUND |

-   Each column is capped at 200 cards; older done cards are paginated.

## API-041 Create task

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/projects/{projectId}/tasks |
| Purpose | 'Create/Edit Task'. |
| Auth | session |
| Permission | Project member |
| Path / query parameters | projectId |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | task.created |
| Domain event | task.created |
| Worker / async | Graph edge works_on for the assignee. |

Request example

    {
      "title": "Payment page",
      "assignee_id": "289b359a-7306-54e2-a6c2-1346e443935a",
      "due_at": "2026-10-15T13:00:00Z",
      "estimate_minutes": 480,
      "billable": true
    }

Success result (201)

    {
      "success": true,
      "message": "Task created.",
      "data": {
        "id": "b0915baf-4b35-57f3-9ed5-869788ad57b8",
        "status": "todo",
        "position": 2,
        "version": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:20:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "ASSIGNEE_NOT_MEMBER",
        "message": "The assignee is not an active member of this company.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created |
| 400 | VALIDATION_FAILED |
| 422 | ASSIGNEE_NOT_MEMBER |

-   Due times are stored in UTC and shown in the company time zone.

## API-042 Edit task

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | PATCH |
| Path | /api/v1/tasks/{taskId} |
| Purpose | Edit title, assignee, due date, estimate, billable. |
| Auth | session |
| Permission | Project member |
| Path / query parameters | taskId |
| Idempotency / concurrency | expected_version required. |
| Audit | task.updated |
| Domain event | task.updated |
| Worker / async | None. |

Request example

    {
      "expected_version": 3,
      "due_at": "2026-10-13T13:00:00Z"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "id": "ab69355b-311b-59bc-b64e-306dd5c5b308",
        "due_at": "2026-10-13T13:00:00Z",
        "version": 4
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T07:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "VERSION_CONFLICT",
        "message": "This task was changed by someone else.",
        "retryable": false,
        "details": {
          "current_version": 4
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Updated |
| 409 | VERSION_CONFLICT |

-   Status changes use API-043.

## API-043 Move task on the board

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/tasks/{taskId}/move |
| Purpose | Drag between Kanban columns or reorder. |
| Auth | session |
| Permission | Project member |
| Path / query parameters | taskId |
| Idempotency / concurrency | expected_version required. |
| Audit | task.moved |
| Domain event | task.status_changed |
| Worker / async | Rules on task.status (e.g. review -> notify owner). |

Request example

    {
      "expected_version": 4,
      "to_status": "review",
      "position": 1
    }

Success result (200)

    {
      "success": true,
      "data": {
        "id": "ab69355b-311b-59bc-b64e-306dd5c5b308",
        "status": "review",
        "position": 1,
        "version": 5
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T12:30:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "INVALID_TRANSITION",
        "message": "Tasks move to Done only from Review.",
        "retryable": false,
        "details": {
          "from": "active",
          "to": "done",
          "allowed": [
            "todo",
            "review"
          ]
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Moved |
| 409 | VERSION_CONFLICT |
| 422 | INVALID_TRANSITION |

-   Allowed: todo<->active, active<->review, review->done, done->review (reopen).

## API-044 Log time manually

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/tasks/{taskId}/time-entries |
| Purpose | Add time not captured by the Room (meetings, offline work). |
| Auth | session |
| Permission | Assignee or project manager |
| Path / query parameters | taskId |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | time.logged |
| Domain event | time.logged |
| Worker / async | unbilled_time detector input. |

Request example

    {
      "started_at": "2026-10-12T10:00:00Z",
      "minutes": 60,
      "billable": true,
      "note": "Client call"
    }

Success result (201)

    {
      "success": true,
      "data": {
        "time_entry_id": "39143e8e-6c52-5b21-be94-c28992020906",
        "source": "manual",
        "minutes": 60,
        "billable": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T11:05:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "TIME_OVERLAPS_SESSION",
        "message": "This time overlaps your Room session, which already counted it.",
        "retryable": false,
        "details": {
          "session_id": "7cda7a88-5bef-558b-b9a9-f8eab5a023c4"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Logged |
| 400 | VALIDATION_FAILED |
| 409 | TIME_OVERLAPS_SESSION |

-   Manual entries cannot overlap a Room session of the same person (prevents double billing).

# 27. CRM and Client Lifecycle Endpoint Contracts

## API-045 Create contact or lead

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/contacts |
| Purpose | 'Contacts and Leads List': add a person and optional company. |
| Auth | session |
| Permission | crm.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required; same email returns the existing contact (unique per company). |
| Audit | contact.created |
| Domain event | contact.created |
| Worker / async | Graph nodes (contact, company). |

Request example

    {
      "name": "Ali Raza",
      "email": "ali@northwind.example",
      "phone": "+923001234567",
      "company": {
        "name": "Northwind Digital",
        "domain": "northwind.example"
      },
      "source": "referral"
    }

Success result (201)

    {
      "success": true,
      "message": "Lead added.",
      "data": {
        "id": "f8da887a-e1b4-5f8c-9b96-ad4ffd1b91bc",
        "lifecycle_stage": "lead",
        "company_id": "1c8ed2b8-d832-57d0-9421-7e63be760862",
        "owner": "Usman Tariq",
        "version": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-09-20T06:00:00Z"
      }
    }

Duplicate email (200)

    {
      "success": true,
      "data": {
        "id": "f8da887a-e1b4-5f8c-9b96-ad4ffd1b91bc",
        "lifecycle_stage": "lead",
        "already_exists": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-09-21T06:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "SUPPRESSED_CONTACT",
        "message": "This email asked not to be contacted. It cannot be added as a lead.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created |
| 200 | Already exists |
| 400 | VALIDATION_FAILED |
| 422 | SUPPRESSED_CONTACT |

-   Suppression list is checked by hashed email/domain (API-060).

## API-046 Search contacts

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/contacts/search |
| Purpose | Filter by stage, owner, source and text; text in the body, not the URL. |
| Auth | session |
| Permission | crm.manage or cfo (read) |
| Path / query parameters | None (body) |
| Idempotency / concurrency | Read-only POST. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "query": "northwind",
      "lifecycle_stage": [
        "lead",
        "qualified",
        "opportunity"
      ],
      "limit": 25,
      "cursor": null
    }

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "f8da887a-e1b4-5f8c-9b96-ad4ffd1b91bc",
            "name": "Ali Raza",
            "company": "Northwind Digital",
            "lifecycle_stage": "opportunity",
            "owner": "Usman Tariq",
            "last_activity_at": "2026-09-28T07:00:00Z"
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Search text must be at least 2 characters.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 400 | VALIDATION_FAILED |

-   Uses pg_trgm indexes on name/email/company (TASK-010).

## API-047 Contact and lead details

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/contacts/{contactId} |
| Purpose | 'Contact/Lead Details' with deals, activities and related people from graph memory. |
| Auth | session |
| Permission | crm.manage or cfo |
| Path / query parameters | contactId |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "id": "f8da887a-e1b4-5f8c-9b96-ad4ffd1b91bc",
        "name": "Ali Raza",
        "email": "ali@northwind.example",
        "company": {
          "id": "1c8ed2b8-d832-57d0-9421-7e63be760862",
          "name": "Northwind Digital"
        },
        "lifecycle_stage": "customer",
        "deals": [
          {
            "id": "fa91f4cf-aa79-5720-86ae-21324ff158ea",
            "title": "Website rebuild",
            "stage": "won",
            "amount": "5000.00",
            "currency": "USD"
          }
        ],
        "activities": [
          {
            "kind": "meeting",
            "note": "Scope workshop",
            "occurred_at": "2026-09-28T07:00:00Z",
            "actor": "Usman Tariq"
          }
        ],
        "related": [
          {
            "kind": "project",
            "label": "Northwind website",
            "via": [
              "contact_of",
              "originated_from",
              "billed_by"
            ]
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Contact not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 404 | NOT_FOUND |

-   `related` comes from ems.graph_neighbors (DB-11), depth 3 max.

## API-048 Create deal

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/deals |
| Purpose | Add an opportunity to the pipeline. |
| Auth | session |
| Permission | crm.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | deal.created |
| Domain event | deal.created |
| Worker / async | Graph edges; contact stage -> opportunity. |

Request example

    {
      "contact_id": "f8da887a-e1b4-5f8c-9b96-ad4ffd1b91bc",
      "title": "Website rebuild",
      "amount": "5000.00",
      "currency": "USD",
      "expected_close": "2026-10-10",
      "owner_id": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f"
    }

Success result (201)

    {
      "success": true,
      "message": "Deal created.",
      "data": {
        "id": "fa91f4cf-aa79-5720-86ae-21324ff158ea",
        "stage": "new",
        "version": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-09-20T06:10:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Amount must be zero or more.",
        "retryable": false,
        "details": {
          "fields": {
            "amount": ">= 0"
          }
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Created |
| 400 | VALIDATION_FAILED |
| 403 | AUTHORIZATION_DENIED |

-   Currency is ISO 4217; amounts are decimal strings.

## API-049 Sales pipeline board

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/deals/pipeline |
| Purpose | 'Sales Pipeline Board' and 'CRM Dashboard' totals. |
| Auth | session |
| Permission | crm.manage or cfo |
| Path / query parameters | owner_id, currency (required if several) |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "currency": "USD",
        "stages": [
          {
            "stage": "new",
            "count": 4,
            "amount": "12000.00"
          },
          {
            "stage": "qualified",
            "count": 3,
            "amount": "9500.00"
          },
          {
            "stage": "proposal",
            "count": 2,
            "amount": "8000.00"
          },
          {
            "stage": "negotiation",
            "count": 1,
            "amount": "6000.00"
          }
        ],
        "weighted_open": "11775.00",
        "won_this_month": {
          "count": 1,
          "amount": "5000.00"
        },
        "stale_count": 2
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "CURRENCY_REQUIRED",
        "message": "Choose a currency; deals exist in USD and PKR.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 400 | CURRENCY_REQUIRED |

-   Weighted = sum(amount x stage probability) using engine/leakage.py STAGE_PROBABILITY.

## API-050 Move deal stage

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/deals/{dealId}/stage |
| Purpose | Advance or lose a deal. |
| Auth | session |
| Permission | crm.manage |
| Path / query parameters | dealId |
| Idempotency / concurrency | expected_version required. |
| Audit | deal.stage_changed |
| Domain event | deal.stage_changed |
| Worker / async | Rules; stale timer resets. |

Request example

    {
      "expected_version": 3,
      "to_stage": "negotiation"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "id": "fa91f4cf-aa79-5720-86ae-21324ff158ea",
        "stage": "negotiation",
        "version": 4
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-02T06:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "INVALID_TRANSITION",
        "message": "Use 'Mark as won' to win a deal.",
        "retryable": false,
        "details": {
          "to": "won",
          "use": "/api/v1/deals/{dealId}/win"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Moved |
| 409 | VERSION_CONFLICT |
| 422 | INVALID_TRANSITION / LOST_REASON_REQUIRED |

-   `lost` requires `lost_reason` (DB-09).

## API-051 Win deal and start client lifecycle

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/deals/{dealId}/win |
| Purpose | One transaction: deal won, client created, kickoff project created from a template, contact becomes customer. |
| Auth | session |
| Permission | crm.manage |
| Path / query parameters | dealId |
| Idempotency / concurrency | Idempotency-Key required; one client per deal (DB-09) so retries return the same client. |
| Audit | deal.won, client.created, project.created |
| Domain event | deal.won |
| Worker / async | Graph edges; won_follow_through detector clears. |

Request example

    {
      "expected_version": 4,
      "project": {
        "name": "Northwind website",
        "billing_type": "fixed",
        "budget_amount": "5000.00",
        "owner_id": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f",
        "template": "website_standard"
      },
      "renewal_date": "2027-10-10"
    }

Success result (200)

    {
      "success": true,
      "message": "Deal won. Client and project created.",
      "data": {
        "deal": {
          "id": "fa91f4cf-aa79-5720-86ae-21324ff158ea",
          "stage": "won",
          "won_at": "2026-10-03T06:00:00Z"
        },
        "client": {
          "id": "6b39c218-ae79-5c7e-b4ca-878c3c7f0e24",
          "status": "onboarding"
        },
        "project": {
          "id": "cb177fe3-6957-56c8-88b8-b33a4a0d61c3",
          "status": "planned",
          "tasks_created": 12
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-03T06:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "ALREADY_WON",
        "message": "This deal is already won.",
        "retryable": false,
        "details": {
          "client_id": "6b39c218-ae79-5c7e-b4ca-878c3c7f0e24"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Won (or replayed) |
| 409 | ALREADY_WON / VERSION_CONFLICT |
| 422 | COMPANY_REQUIRED |

-   Without a project the won deal shows a leakage finding after 3 days (LEK-04).

## API-052 Log activity

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/activities |
| Purpose | Call, email, meeting or note on a contact, deal, client or project. |
| Auth | session |
| Permission | crm.manage or project member |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | activity.created |
| Domain event | activity.created |
| Worker / async | Updates deal.last_activity_at (stale timer). |

Request example

    {
      "entity_type": "deal",
      "entity_id": "fa91f4cf-aa79-5720-86ae-21324ff158ea",
      "kind": "call",
      "note": "Agreed payment terms",
      "occurred_at": "2026-10-02T05:30:00Z"
    }

Success result (201)

    {
      "success": true,
      "data": {
        "id": "e48de246-ca83-5193-8f7d-eb498df178b6",
        "entity_type": "deal",
        "entity_id": "fa91f4cf-aa79-5720-86ae-21324ff158ea"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-02T05:31:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Activity time cannot be in the future.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Logged |
| 400 | VALIDATION_FAILED |
| 404 | NOT_FOUND |

-   Activities are append-only.

## API-053 Record invoice

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/invoices |
| Purpose | Record an invoice issued to a client (EMS does not send or collect payment in Release 1). |
| Auth | session |
| Permission | finance.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required; number unique per company. |
| Audit | invoice.recorded |
| Domain event | invoice.recorded |
| Worker / async | Marks included time entries invoiced; leakage detectors. |

Request example

    {
      "client_id": "6b39c218-ae79-5c7e-b4ca-878c3c7f0e24",
      "project_id": "cb177fe3-6957-56c8-88b8-b33a4a0d61c3",
      "number": "INV-2026-1048",
      "amount": "2500.00",
      "currency": "USD",
      "issued_on": "2026-10-05",
      "due_on": "2026-10-19",
      "time_entry_ids": []
    }

Success result (201)

    {
      "success": true,
      "message": "Invoice INV-2026-1048 recorded.",
      "data": {
        "id": "a16f7130-ffc6-5dc6-99c0-05a9af40850c",
        "status": "sent",
        "outstanding": "2500.00"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-05T06:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "INVOICE_NUMBER_TAKEN",
        "message": "Invoice number INV-2026-1048 already exists.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Recorded |
| 400 | VALIDATION_FAILED - due before issue |
| 409 | INVOICE_NUMBER_TAKEN |

-   Billing integration (sending invoices, online payment) is Release 2 (report: 'Billing (future)').

## API-054 Record payment

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/invoices/{invoiceId}/payments |
| Purpose | Record money received; status becomes partially_paid or paid. |
| Auth | session |
| Permission | finance.manage |
| Path / query parameters | invoiceId |
| Idempotency / concurrency | Idempotency-Key required; payments are append-only. |
| Audit | payment.recorded |
| Domain event | payment.recorded |
| Worker / async | overdue_invoice findings resolve automatically. |

Request example

    {
      "amount": "2500.00",
      "received_on": "2026-10-18",
      "method": "bank_transfer"
    }

Success result (201)

    {
      "success": true,
      "data": {
        "payment_id": "c1254628-c06c-5084-b8c5-bae99416d450",
        "invoice_status": "paid",
        "outstanding": "0.00"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-18T06:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "OVERPAYMENT",
        "message": "Payment exceeds the outstanding amount of 2500.00 USD.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Recorded |
| 422 | OVERPAYMENT |

-   Corrections are negative adjustments in Release 2; Release 1 voids and re-records.

# 28. Lead Hunter Endpoint Contracts

## API-055 Start a hunt

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/hunts |
| Purpose | 'Search and Filters': crawl user-supplied company websites and score them against an ideal-customer profile. |
| Auth | session |
| Permission | hunter.use |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required. |
| Audit | hunt.created |
| Domain event | hunt.created |
| Worker / async | Crawler job (robots.txt per RFC 9309, 1 request / 5 s per domain). |

Request example

    {
      "name": "Lahore marketing agencies",
      "seeds": {
        "domains": [
          "brightpixel.example",
          "adsmiths.example",
          "northwind.example"
        ]
      },
      "icp": {
        "industry_keywords": [
          "marketing agency",
          "digital agency"
        ],
        "countries": [
          "PK"
        ],
        "tech": [
          "wordpress",
          "shopify"
        ],
        "min_team_size": 10
      },
      "max_pages_per_domain": 5
    }

Success result (202)

    {
      "success": true,
      "message": "Hunt started.",
      "data": {
        "hunt_id": "a5c53104-0195-532f-9cb5-21bb085d220d",
        "status": "queued",
        "domains": 3,
        "estimated_minutes": 2
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "SOURCE_NOT_ALLOWED",
        "message": "linkedin.com cannot be crawled. Use company websites you are allowed to visit.",
        "retryable": false,
        "details": {
          "domain": "linkedin.com"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 202 | Queued |
| 400 | VALIDATION_FAILED - max 200 domains |
| 422 | SOURCE_NOT_ALLOWED |

-   Release 1 seeds are domains the user supplies or imports; EMS does not scrape search engines or social networks (blocklist: linkedin.com, facebook.com, instagram.com, x.com, google.* search).

-   Only pages allowed by robots.txt are fetched; 5xx/unreachable robots.txt means do not crawl (ROB-03).

## API-056 Hunt status

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/hunts/{huntId} |
| Purpose | 'Lead Hunter Dashboard': progress and crawl outcomes. |
| Auth | session |
| Permission | hunter.use |
| Path / query parameters | huntId |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "hunt_id": "a5c53104-0195-532f-9cb5-21bb085d220d",
        "status": "completed",
        "stats": {
          "domains": 3,
          "fetched_pages": 11,
          "robots_disallowed": 2,
          "unreachable": 0,
          "prospects": 2,
          "already_in_crm": 1
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:03:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Hunt not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 404 | NOT_FOUND |

-   `already_in_crm` domains are skipped, not duplicated.

## API-057 Results and scoring

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/hunts/{huntId}/prospects |
| Purpose | 'Results and Scoring' with reasons for every point. |
| Auth | session |
| Permission | hunter.use |
| Path / query parameters | huntId, min_score, cursor |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "f0075a89-77cf-5d3d-9e28-9e37f2339004",
            "domain": "brightpixel.example",
            "company_name": "BrightPixel",
            "score": 85,
            "score_reasons": [
              "industry keywords: marketing agency",
              "country PK",
              "contact page found",
              "public business email listed",
              "uses wordpress"
            ],
            "public_emails": [
              "info@brightpixel.example"
            ],
            "source_url": "https://brightpixel.example/about",
            "status": "new"
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:03:30Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Hunt not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 404 | NOT_FOUND |

-   Only role addresses published on the site (info@, sales@, contact@) are stored; personal emails are not collected.

## API-058 Promote prospect to CRM

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/prospects/{prospectId}/promote |
| Purpose | Create company + contact (role address) as a lead with source lead_hunter. |
| Auth | session |
| Permission | hunter.use + crm.manage |
| Path / query parameters | prospectId |
| Idempotency / concurrency | Repeat returns the same contact. |
| Audit | prospect.promoted |
| Domain event | contact.created |
| Worker / async | Graph nodes. |

Request example

    {
      "owner_id": "d020ad78-8e9e-5cb5-ace0-e3c092fd4c8f"
    }

Success result (201)

    {
      "success": true,
      "message": "BrightPixel added to CRM.",
      "data": {
        "contact_id": "041f7634-1a7e-5c02-ae2c-cff0cfb5d5db",
        "company_id": "b3a75df0-9029-5ca6-8389-c173a6d6a357",
        "lifecycle_stage": "lead"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:10:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "SUPPRESSED_CONTACT",
        "message": "This domain asked not to be contacted.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Promoted |
| 422 | SUPPRESSED_CONTACT |

-   Prospect status becomes `promoted`.

## API-059 Draft outreach email

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/prospects/{prospectId}/outreach-draft |
| Purpose | 'Outreach Email Draft': template-based draft using the prospect's signals; the user edits and sends from their own mailbox. |
| Auth | session |
| Permission | hunter.use |
| Path / query parameters | prospectId |
| Idempotency / concurrency | Read-only computation. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "template": "intro_services",
      "sender_name": "Usman Tariq",
      "offer": "website maintenance"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "subject": "Website maintenance for BrightPixel",
        "body": "Hi BrightPixel team,\n\nI saw on your site that you build WordPress sites for marketing clients. Acme Tech handles website maintenance so agencies like yours can focus on clients.\n\nWould a 15-minute call next week be useful?\n\nUsman Tariq\nAcme Tech\n\nIf you prefer not to hear from us, reply 'unsubscribe' and we will not contact you again.",
        "template": "intro_services",
        "fields_used": [
          "company_name",
          "tech",
          "sender_name",
          "offer"
        ],
        "send_via": "copy_to_mail_client"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:12:00Z"
      }
    }

Error result (422)

    {
      "success": false,
      "error": {
        "code": "SUPPRESSED_CONTACT",
        "message": "This domain asked not to be contacted.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Draft |
| 422 | SUPPRESSED_CONTACT |

-   Release 1 never sends email automatically; sequences are Release 2 and need INT-003 and an opt-out flow.

-   Every draft includes an opt-out line.

## API-060 Add to do-not-contact list

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/suppressions |
| Purpose | Record opt-outs and bounces; blocks future promotion and drafts. |
| Auth | session |
| Permission | hunter.use or crm.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotent per (kind, value). |
| Audit | suppression.added |
| Domain event | suppression.added |
| Worker / async | Mark matching prospects suppressed. |

Request example

    {
      "kind": "domain",
      "value": "adsmiths.example",
      "reason": "opt_out"
    }

Success result (201)

    {
      "success": true,
      "data": {
        "kind": "domain",
        "stored_as": "sha256",
        "prospects_suppressed": 1
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:15:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Enter a valid email or domain.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Added |
| 400 | VALIDATION_FAILED |

-   Only the SHA-256 of the normalized value is stored.

# 29. Automation and Rules Endpoint Contracts

## API-061 Automation dashboard

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/rules |
| Purpose | 'Automation Dashboard': rules, last run and match counts. |
| Auth | session |
| Permission | rules.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "95510c77-2c22-5a8e-93d8-ee41862bcc20",
            "key": "stale_deal_nudge",
            "version": 1,
            "trigger": "deal.stale",
            "enabled": true,
            "runs_7d": 14,
            "matched_7d": 3,
            "failed_7d": 0
          }
        ],
        "external_api_calls_7d": 0
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "Only leadership can manage automations.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   `external_api_calls_7d` is shown because the product promise is API-light; Release 1 rules make none.

## API-062 Create rule

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/rules |
| Purpose | Save a rule definition (new key or new version). |
| Auth | session |
| Permission | rules.manage |
| Path / query parameters | None |
| Idempotency / concurrency | Idempotency-Key required; (key, version) unique. |
| Audit | rule.created |
| Domain event | rule.created |
| Worker / async | None. |

Request example

    {
      "key": "stale_deal_nudge",
      "definition": {
        "trigger": "deal.stale",
        "when": {
          "all": [
            {
              "fact": "deal.days_since_activity",
              "op": "gte",
              "value": 14
            },
            {
              "any": [
                {
                  "fact": "deal.stage",
                  "op": "in",
                  "value": [
                    "proposal",
                    "negotiation"
                  ]
                }
              ]
            }
          ]
        },
        "then": [
          {
            "action": "notify",
            "to": "owner",
            "template": "deal_stale"
          },
          {
            "action": "create_task",
            "assign": "owner",
            "title": "Follow up: {deal.title}",
            "due_in_hours": 24
          }
        ]
      }
    }

Success result (201)

    {
      "success": true,
      "message": "Rule saved.",
      "data": {
        "id": "95510c77-2c22-5a8e-93d8-ee41862bcc20",
        "key": "stale_deal_nudge",
        "version": 1,
        "enabled": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-01T07:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "RULE_INVALID",
        "message": "Fact 'deal.secret' is not available for trigger deal.stale.",
        "retryable": false,
        "details": {
          "reason": "FACT_NOT_ALLOWED:deal.secret"
        }
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 201 | Saved |
| 400 | RULE_INVALID (engine/rules.py validate, RUL-03) |
| 403 | AUTHORIZATION_DENIED |

-   No code, regular expressions or URLs are accepted.

## API-063 Simulate rule

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/rules/{ruleId}/simulate |
| Purpose | Run a rule against sample facts; no side effects. |
| Auth | session |
| Permission | rules.manage |
| Path / query parameters | ruleId |
| Idempotency / concurrency | Read-only computation. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Request example

    {
      "facts": {
        "deal.days_since_activity": 15,
        "deal.stage": "proposal",
        "deal.title": "Website rebuild"
      }
    }

Success result (200)

    {
      "success": true,
      "data": {
        "matched": true,
        "trace": [
          {
            "fact": "deal.days_since_activity",
            "op": "gte",
            "value": 14,
            "actual": 15,
            "result": true
          },
          {
            "fact": "deal.stage",
            "op": "in",
            "value": [
              "proposal",
              "negotiation"
            ],
            "actual": "proposal",
            "result": true
          }
        ],
        "actions": [
          {
            "action": "notify",
            "to": "owner",
            "template": "deal_stale"
          },
          {
            "action": "create_task",
            "assign": "owner",
            "title": "Follow up: Website rebuild",
            "due_in_hours": 24
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Rule not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Simulated |
| 404 | NOT_FOUND |

-   Output is exactly engine/rules.py run() (RUL-01).

## API-064 Workflow execution logs

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/rule-runs |
| Purpose | 'Workflow Execution Logs and Alerts'. |
| Auth | session |
| Permission | rules.manage |
| Path / query parameters | rule_id, outcome, cursor |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "bf51d58a-6fa0-52ec-8449-0ff16d9a8e63",
            "rule": "stale_deal_nudge",
            "event": "deal.stale",
            "outcome": "matched",
            "actions": [
              "notify",
              "create_task"
            ],
            "ran_at": "2026-10-12T01:00:00Z"
          }
        ],
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "Only leadership can view automation logs.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   One run per (rule, event) (DB-12); loops are cut at chain depth 3 (`skipped_loop`).

# 30. Revenue Engine and Dashboards Endpoint Contracts

## API-065 Revenue leakage findings

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/leakage/findings |
| Purpose | CEO/CFO list of money at risk with evidence. |
| Auth | session |
| Permission | leakage.read (CEO, CFO, COO) |
| Path / query parameters | status, kind, cursor |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | Nightly detector run at 01:00 company time. |

Success result (200)

    {
      "success": true,
      "data": {
        "totals": {
          "open": 3,
          "amount_at_risk": "8620.00",
          "currency": "USD"
        },
        "items": [
          {
            "id": "0b11ee2e-7988-5265-8a7b-9479b8d4071a",
            "kind": "overdue_invoice",
            "label": "INV-2026-1031 overdue 11 days",
            "amount_at_risk": "6000.00",
            "currency": "USD",
            "evidence": {
              "number": "INV-2026-1031",
              "days_overdue": 11
            },
            "detected_at": "2026-10-12T20:00:00Z"
          },
          {
            "id": "2a3b0459-948a-5ada-bf98-8355471d4ee0",
            "kind": "stale_deal",
            "label": "Contoso redesign - no activity 17 days",
            "amount_at_risk": "2500.00",
            "currency": "USD",
            "evidence": {
              "stage": "proposal",
              "days_without_activity": 17,
              "weighting": "0.50",
              "deal_amount": "5000.00"
            },
            "detected_at": "2026-10-12T20:00:00Z"
          },
          {
            "id": "d217d558-6b2c-57d3-b6fb-74ed1b96be02",
            "kind": "unbilled_time",
            "label": "Contoso support - 3 h unbilled",
            "amount_at_risk": "120.00",
            "currency": "USD",
            "evidence": {
              "minutes": 180,
              "entries": 1
            },
            "detected_at": "2026-10-12T20:00:00Z"
          }
        ],
        "note": "Amounts are estimates of money at risk."
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-13T04:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "Only the CEO, CFO and COO can see leakage findings.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   Detectors and formulas: Section 17 and engine/leakage.py (LEK-01..06).

## API-066 Resolve or dismiss finding

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/leakage/findings/{findingId}/resolve |
| Purpose | Record the action taken (invoiced, followed up, dismissed with reason). |
| Auth | session |
| Permission | leakage.resolve (CEO, CFO) |
| Path / query parameters | findingId |
| Idempotency / concurrency | First resolution wins. |
| Audit | leakage.resolved |
| Domain event | leakage.resolved |
| Worker / async | None. |

Request example

    {
      "resolution": "resolved",
      "note": "Reminder sent; client promised payment Friday"
    }

Success result (200)

    {
      "success": true,
      "data": {
        "id": "0b11ee2e-7988-5265-8a7b-9479b8d4071a",
        "status": "resolved",
        "resolved_by": "Omar Siddiqui",
        "resolved_at": "2026-10-13T05:00:00Z"
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-13T05:00:00Z"
      }
    }

Error result (409)

    {
      "success": false,
      "error": {
        "code": "ALREADY_RESOLVED",
        "message": "This finding was already resolved.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Resolved |
| 400 | VALIDATION_FAILED - note required for dismissed |
| 409 | ALREADY_RESOLVED |

-   A resolved finding reappears only if its fingerprint changes (new due date, new period).

## API-067 Role-based dashboard

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/dashboards/{role} |
| Purpose | Six dashboard variants (ceo, cto, cfo, coo, hr, employee) with only metrics EMS can source. |
| Auth | session |
| Permission | dashboards.all for CEO; others only their own role |
| Path / query parameters | role, period (this_month\|last_30_days) |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | Cached 5 minutes per org and role. |

Success result (200)

    {
      "success": true,
      "data": {
        "role": "cfo",
        "period": {
          "label": "October 2026",
          "from": "2026-10-01",
          "to": "2026-10-31"
        },
        "currency": "USD",
        "tiles": [
          {
            "key": "invoiced",
            "label": "Invoiced this month",
            "value": "18450.00",
            "source": "invoices"
          },
          {
            "key": "collected",
            "label": "Collected",
            "value": "11600.00",
            "source": "payments"
          },
          {
            "key": "outstanding",
            "label": "Outstanding invoices",
            "value": "6850.00",
            "count": 4,
            "source": "invoices - payments"
          },
          {
            "key": "leakage",
            "label": "Revenue at risk",
            "value": "8620.00",
            "source": "leakage_findings"
          }
        ],
        "budget_projects": [
          {
            "project": "Northwind website",
            "budget": "5000.00",
            "cost_to_date": "1820.00",
            "ratio": "0.36"
          }
        ],
        "unavailable": [
          {
            "key": "operating_expenses",
            "reason": "No accounting integration in Release 1"
          },
          {
            "key": "net_profit",
            "reason": "Needs operating expenses"
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-13T04:00:00Z"
      }
    }

Error result (403)

    {
      "success": false,
      "error": {
        "code": "AUTHORIZATION_DENIED",
        "message": "You can only open your own role's dashboard.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 403 | AUTHORIZATION_DENIED |

-   Every tile names its source; a metric without a source is listed under `unavailable` instead of showing sample data (Section 18).

## API-068 Graph memory: related items

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/graph/neighbors |
| Purpose | 'Related' panels: people, clients, projects and deals connected to an item. |
| Auth | session |
| Permission | Results filtered by the caller's read permissions |
| Path / query parameters | kind, ref_id, depth (1-3) |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "node": {
          "kind": "person",
          "label": "Bilal Ahmed"
        },
        "neighbors": [
          {
            "kind": "project",
            "label": "Northwind website",
            "depth": 1,
            "via": [
              "works_on"
            ]
          },
          {
            "kind": "client",
            "label": "Northwind Digital",
            "depth": 2,
            "via": [
              "works_on",
              "billed_by"
            ]
          }
        ]
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:00:00Z"
      }
    }

Error result (400)

    {
      "success": false,
      "error": {
        "code": "VALIDATION_FAILED",
        "message": "Depth must be 1, 2 or 3.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 400 | VALIDATION_FAILED |
| 404 | NOT_FOUND |

-   Backed by ems.graph_neighbors() under RLS (DB-11); no external graph database.

## API-069 Notifications

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | GET |
| Path | /api/v1/notifications |
| Purpose | 'Notifications' screen. |
| Auth | session |
| Permission | Own notifications |
| Path / query parameters | unread_only, cursor |
| Idempotency / concurrency | Read-only. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Success result (200)

    {
      "success": true,
      "data": {
        "items": [
          {
            "id": "b285c048-87d0-5a1d-a2fb-68ca95133529",
            "kind": "leave.requested",
            "title": "Bilal Ahmed requested 3 days annual leave",
            "ref_type": "leave_request",
            "ref_id": "926408eb-ff9a-5b9b-9bb8-002245f807af",
            "read": false,
            "created_at": "2026-10-12T06:00:00Z"
          }
        ],
        "unread": 1,
        "next_cursor": null
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:05:00Z"
      }
    }

Error result (401)

    {
      "success": false,
      "error": {
        "code": "AUTHENTICATION_REQUIRED",
        "message": "Your session has expired. Sign in again.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Success |
| 401 | AUTHENTICATION_REQUIRED |

-   Delivered in-app in Release 1; email copies need INT-003.

## API-070 Mark notification read

| Item | Contract |
|------------------------|--------------------------------------------------------|
| Method | POST |
| Path | /api/v1/notifications/{notificationId}/read |
| Purpose | Mark one notification read. |
| Auth | session |
| Permission | Owner |
| Path / query parameters | notificationId |
| Idempotency / concurrency | Idempotent. |
| Audit | None. |
| Domain event | None. |
| Worker / async | None. |

Request example

    {}

Success result (200)

    {
      "success": true,
      "data": {
        "id": "b285c048-87d0-5a1d-a2fb-68ca95133529",
        "read": true
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21",
        "timestamp": "2026-10-12T06:06:00Z"
      }
    }

Error result (404)

    {
      "success": false,
      "error": {
        "code": "NOT_FOUND",
        "message": "Notification not found.",
        "retryable": false,
        "details": {}
      },
      "meta": {
        "api_version": "v1",
        "request_id": "req_7f3a9c21"
      }
    }

| HTTP | Meaning |
|------|------------------------------------------------|
| 200 | Marked |
| 404 | NOT_FOUND |

-   Deleting notifications is not offered; they expire after 90 days.

# 31. State Machines and Domain Events

## 31.1 State machines

| Object | States | Allowed transitions |
|---|---|---|
| Organization setup | account_created, company_setup_done, team_invited, active | in order; `active` also from any state via "Skip for now" |
| Invitation | pending, accepted, expired, revoked | pending -> accepted / expired / revoked |
| Work session | open, closed, auto_closed | open -> closed (check-out) / auto_closed (2 h after work end, at last heartbeat) |
| Presence | active, idle, locked, on_break, offline | any -> any, derived by the server on each heartbeat or timeout |
| Break | requested, approved, rejected, active, ended | requested -> approved -> active -> ended; requested -> rejected; within allowance: created as active |
| Leave request | pending, approved, rejected, cancelled | pending -> approved / rejected / cancelled; approved -> cancelled (before start) |
| Task | todo, active, review, done | Section 12 |
| Deal | new, qualified, proposal, negotiation, won, lost | open stages move freely; any open -> lost (reason); open -> won only via API-051 |
| Client | onboarding, active, at_risk, churned | Section 13 |
| Project | planned, active, on_hold, completed, cancelled | planned -> active -> on_hold <-> active -> completed; planned/active/on_hold -> cancelled |
| Invoice | draft, sent, partially_paid, paid, void | sent -> partially_paid -> paid; sent/partially_paid -> void (no payments only) |
| Hunt | queued, running, completed, failed, cancelled | queued -> running -> completed / failed; queued/running -> cancelled |
| Prospect | new, promoted, discarded, suppressed | new -> promoted / discarded / suppressed |
| Leakage finding | open, resolved, dismissed | open -> resolved / dismissed (dismissed needs a note) |

## 31.2 Domain events (outbox `routing_key`)

Every event is written to `outbox_events` in the same transaction as the business change; the worker publishes it to in-process handlers (rules, notifications, graph edges) and marks it published (DB-14). Handlers must be idempotent by event ID.

| Event | Emitted by | Handled by |
|---|---|---|
| org.created, org.updated | API-002, API-010 | Audit |
| member.invited, member.joined, member.role_changed, member.deactivated | API-011..015 | Notifications, graph (reports_to), Room (revoke tokens) |
| room.consent_changed, room.checked_in, room.presence_changed, room.checked_out | API-017..020 | Rules (attendance.late), dashboards cache, daily totals |
| room.break_requested, room.break_decided, room.break_ended | API-021..023 | Notifications |
| room.stream_state, room.view_started | API-024, API-026 | Extension notice to the employee |
| leave.requested, leave.decided | API-031, API-033 | Rules (leave.requested), notifications |
| policy.published | API-037 | Rules reload; consent version bump for `monitoring` |
| project.created, task.created, task.updated, task.status_changed, time.logged | API-039..044 | Graph, rules (task.overdue), leakage inputs |
| contact.created, deal.created, deal.stage_changed, deal.won, activity.created | API-045..052, API-058 | Graph, rules (deal.stale timer), leakage |
| invoice.recorded, payment.recorded | API-053, API-054 | Leakage auto-resolve |
| hunt.created, suppression.added | API-055, API-060 | Crawler, prospect suppression |
| rule.created, leakage.resolved | API-062, API-066 | Audit |

# 32. Privacy, Security and Logging

-   **Data minimization:** the Room collects only Section 9.1 items; no media is stored by EMS or LiveKit (LiveKit egress/recording is not installed).
-   **Retention:** presence segments and stream views 12 months; agent logs 90 days; crawl log 90 days; notifications 90 days; audit events 24 months. A nightly job deletes older rows (TASK-017).
-   **Secrets:** environment variables only (Section 34); never in the database, logs or the extension bundle. The LiveKit API secret never leaves the API.
-   **Passwords:** argon2id (argon2-cffi 25.1.0 defaults), 12-128 characters, common-password list check.
-   **Tokens:** sessions, invitations, password resets and extension tokens are 32 random bytes; only SHA-256 hashes are stored.
-   **Logging:** JSON logs with `request_id`, `org_id`, `user_id`, route, status, duration. Never log request bodies, cookies, tokens, passwords, emails, HR Agent questions, or LiveKit tokens.
-   **Audit:** every row in the endpoint contracts' "Audit" line writes `audit_events` (actor, action, record type and id, changed field names - not values). Audit rows are insert-only (DB-13).
-   **Headers:** HSTS, `Content-Security-Policy` with `connect-src` limited to the API and LiveKit origins, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`.
-   **No compliance claim:** this document does not claim compliance with any privacy law or certification. OD-02 covers the monitoring review.

# 33. Error Catalogue

| Code | HTTP | Retryable | Meaning / user message theme |
|---|---|---|---|
| VALIDATION_FAILED | 400 | no | Field errors in `details.fields` |
| STATE_MISMATCH | 400 | no | Google sign-in state did not match; start again |
| CURRENCY_REQUIRED | 400 | no | Several currencies exist; choose one |
| RULE_INVALID | 400 | no | Rule definition rejected; `details.reason` from the engine |
| AUTHENTICATION_REQUIRED | 401 | no | Not signed in or session expired |
| INVALID_CREDENTIALS | 401 | no | Email or password incorrect |
| AUTHORIZATION_DENIED | 403 | no | Role lacks the permission |
| ORG_NOT_SELECTED | 403 | no | User belongs to several companies; send `X-Org-Id` |
| INVITATION_EMAIL_MISMATCH | 403 | no | Invitation was for another email |
| GOOGLE_ACCOUNT_NOT_LINKED | 403 | no | No EMS user for this Google account |
| CONSENT_REQUIRED | 403 | no | Monitoring notice not accepted |
| ON_BREAK | 403 | no | Cannot share while on break |
| ON_APPROVED_LEAVE | 403 | no | Cannot check in on approved leave |
| NOT_FOUND | 404 | no | Record missing or in another company (same response) |
| VERSION_CONFLICT | 409 | no | Reload; `details.current_version` |
| IDEMPOTENCY_KEY_REUSED | 409 | no | Same key used with a different body |
| SLUG_TAKEN | 409 | no | Company address in use |
| EMAIL_IN_USE | 409 | no | An account with this email exists; sign in |
| POLICY_VERSION_OUTDATED | 409 | no | Accept the newer notice |
| SESSION_CLOSED | 409 | no | Work session ended |
| NO_OPEN_SESSION | 409 | no | Not checked in |
| BREAK_ALREADY_ACTIVE | 409 | no | A break is already running |
| ALREADY_DECIDED | 409 | no | Break request already decided |
| STREAM_NOT_LIVE | 409 | no | Employee is not sharing now |
| LEAVE_OVERLAP | 409 | no | Overlapping leave exists |
| TIME_OVERLAPS_SESSION | 409 | no | Manual time overlaps a Room session |
| ALREADY_WON | 409 | no | Deal already won |
| INVOICE_NUMBER_TAKEN | 409 | no | Invoice number exists |
| ALREADY_RESOLVED | 409 | no | Finding already resolved |
| INVITATION_INVALID | 410 | no | Invitation expired, used or revoked |
| RESET_TOKEN_EXPIRED | 410 | no | Reset link expired or used |
| ONE_CEO_ONLY | 422 | no | Exactly one CEO per company |
| CANNOT_DEACTIVATE_CEO | 422 | no | CEO cannot be deactivated |
| INSUFFICIENT_BALANCE | 422 | no | Not enough leave balance |
| ASSIGNEE_NOT_MEMBER | 422 | no | Assignee not an active member |
| INVALID_TRANSITION | 422 | no | Status move not allowed; `details.allowed` |
| LOST_REASON_REQUIRED | 422 | no | Lost deals need a reason |
| COMPANY_REQUIRED | 422 | no | Win needs a company on the contact |
| OVERPAYMENT | 422 | no | Payment above outstanding |
| SOURCE_NOT_ALLOWED | 422 | no | Domain is on the crawl blocklist |
| SUPPRESSED_CONTACT | 422 | no | Do-not-contact list match |
| MEMBER_DEACTIVATED | 423 | no | Membership deactivated |
| RATE_LIMITED | 429 | yes | Retry after `Retry-After` seconds |
| INTERNAL_ERROR | 500 | yes | Unexpected error; `request_id` for support |
| GOOGLE_NOT_CONFIGURED | 503 | no | Google sign-in not set up for this deployment |
| MEDIA_UNAVAILABLE | 503 | yes | LiveKit unreachable; presence keeps working |

# 34. Configuration and Environment Variables

| Variable | Example (synthetic) | Used by |
|---|---|---|
| DATABASE_URL | postgresql+psycopg://ems_app:...@db.internal:5432/ems | API |
| WORKER_DATABASE_URL | postgresql+psycopg://ems_worker:...@db.internal:5432/ems | Worker |
| APP_BASE_URL | https://app.ems.example | API (links, CORS, cookies) |
| SESSION_COOKIE_SECURE | true | API |
| CSRF_SECRET | 64 random hex characters | API |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | from Google Cloud console (OD-07) | API; empty -> `GOOGLE_NOT_CONFIGURED` |
| LIVEKIT_URL | wss://media.ems.example | API (returned to clients) |
| LIVEKIT_API_KEY / LIVEKIT_API_SECRET | from the LiveKit server config | API only |
| EXTENSION_ID | Chrome extension ID (OD-03) | API (CORS allow-list for `chrome-extension://<id>`) |
| CRAWLER_USER_AGENT | EMS-LeadHunter/1.0 (+https://app.ems.example/bot) | Worker |
| EMAIL_PROVIDER | none | API, worker; any other value is BLOCKED until INT-003 |
| AI_REPHRASER | disabled | API; any other value refused at start-up until INT-006 |
| LOG_LEVEL | info | All |

The API refuses to start if a required variable is missing or if `AI_REPHRASER` / `EMAIL_PROVIDER` name an adapter that is not implemented (no fake success path).

# 35. Repository Layout, CI/CD and AWS Deployment

    ems/
      backend/app/{main.py, auth/, org/, room/, hr/, agent/, projects/, crm/, finance/, hunter/, rules/, graph/, leakage/, dashboards/, platform/}
      backend/app/engine/ -> copy of pack engine/ (rules, presence, leakage, robots, scoring, hr_agent)
      backend/migrations/  (Alembic; 0001 = db/001 + db/002)
      backend/tests/       (pytest: API contract tests from contracts/api-examples.json)
      worker/              (outbox loop, crawler, nightly jobs; same package as backend)
      web/                 (Next.js 16.4.0)
      extension/           (Manifest V3)
      infra/               (container definitions, LiveKit config)

-   **CI (every pull request):** lint, `python -m unittest engine.tests.test_engine`, `verify_ems_db.py` against a disposable PostgreSQL 17 service container, API contract tests, `tools/check_spec.py`, Next.js build, extension build.
-   **CD:** main branch -> beta environment automatically; production by manual approval. The report's CI/CD tool choice remains with the team (OD-04); GitHub Actions is the proposed default because the steps above are plain shell commands.
-   **AWS reference:** ECS Fargate (2 API tasks, 1 worker task) behind an Application Load Balancer; RDS PostgreSQL 17 Multi-AZ with automated backups; LiveKit on one EC2 instance with a public IP and the UDP ports from LiveKit's deployment guide (to be inspected in TASK-011 - Appendix G gap); S3 + CloudFront for the web build.
-   **Migrations:** run as an admin role in a one-off task before the new API version starts; the API never runs DDL.

# 36. Tests and Release No-Go Gates

| Gate | Check | Status today |
|---|---|---|
| G1 Isolation | DB-01..DB-18 on PostgreSQL 17 in CI | DB-01..18 PASS on PostgreSQL 16.13 (sandbox) |
| G2 Engine | 21 engine tests | PASS (Python 3.11.15) |
| G3 Contracts | Every API in `contracts/api-examples.json` returns the documented status codes and envelope (TEST-001) | Not run - API not built |
| G4 Room privacy | TEST-002: extension sends no URL, title, screenshot or keystroke (network capture of a 10-minute session) | Not run |
| G5 Viewing transparency | TEST-003: every view creates a `stream_views` row and an employee notice within 5 s | Not run |
| G6 Crawler manners | TEST-004: robots.txt 5xx blocks crawl; disallowed paths never fetched; 1 request / 5 s per domain | Unit part ROB-01..03 PASS; integration not run |
| G7 Leakage accuracy | TEST-005: fixture produces exactly the 3 findings and $8,620.00 in API-065 | Unit part LEK-01..06 PASS |
| G8 Concurrency | TEST-006: 20 parallel check-ins, Win replays and invoice payments give single outcomes | DB part DB-06, DB-09 PASS |
| G9 No fake integrations | TEST-007: with `EMAIL_PROVIDER=none` invites return copy links; Google unset returns 503; no UI shows "sent" | Not run |
| G10 Tokens | LK-01..03 LiveKit grant checks | PASS (livekit-api 1.2.1) |

Release 1 does not ship to the pilot if any gate fails. G4 and G5 must pass before OD-02 can switch on live viewing.

# 37. Release 1 Definition of Done

1.  All 70 operations implemented and passing TEST-001.
2.  Gates G1..G10 pass in CI on PostgreSQL 17.
3.  The journey in Section 2.2 runs end to end on beta with the synthetic fixture.
4.  Six dashboards show only sourced tiles; unavailable tiles show their reason.
5.  Extension consent, check-in, presence, breaks and Media Session Page work on Chrome stable on Windows and macOS.
6.  Open owner decisions are either closed or their features stay switched off with a visible label.
7.  Asra's API documentation is generated from `contracts/api-examples.json`, not retyped.

# Appendix A - Release 1 API Count by Domain

| Domain | Operations |
|---|---|
| System and Authentication | 9 |
| Company and Team | 7 |
| Live Employee Room | 12 |
| People and HR (including HR Agent) | 9 |
| Projects and Tasks | 7 |
| CRM and Client Lifecycle | 10 |
| Lead Hunter | 6 |
| Automation and Rules | 4 |
| Revenue Engine and Dashboards | 6 |
| **TOTAL** | **70** |

# Appendix B - Release 2 Handoff (Not Implemented in This Document)

| Report Week 2 item | Release 2 starting point | Precondition |
|---|---|---|
| Employee onboarding, payroll and salary | New HR module on memberships + cost_rate | Payroll rules per country (owner) |
| Leave policy enhancements | hr_policies rules JSON | - |
| Recording history, multi-monitor view | LiveKit egress; retention policy | OD-02 legal review; storage budget |
| Idle detection (advanced) | presence_segments already stored | Agree with HR that no automatic penalty applies |
| Pipeline analytics, email sync, communication history | activities table; email provider adapter | INT-003 |
| Email sequences, LinkedIn sources, campaigns | suppression_list, drafts | OD-05; LinkedIn only through an official, licensed API |
| Task time tracking, Gantt | time_entries, tasks.due_at | - |
| Client-facing workflow builder | rules engine JSON + simulator | UI design |
| Custom roles, advanced permissions, audit log UI | permission matrix, audit_events | - |
| Subscription plans, invoices and payment history (billing for EMS itself) | New billing module | Payment provider choice |
| CTO and CFO external metrics | Monitoring / CI / accounting connectors | Provider choice per customer |
| Optional language-model rephrasing | INT-006 interface | OD-06 |

# Appendix C - Decision Register and Open Owner Decisions

Engineering decisions DEC-001 to DEC-012 are in Section 6.2 (proposed by the technical lead; reversible with the stated consequence). The decisions below belong to the product owner because they change legal exposure, cost or scope.

| ID | Decision needed | Owner | Blocks | Default until decided |
|---|---|---|---|---|
| OD-01 | Confirm the must-work tier (Section 5) and the demo modules | CEO + Subhan (PMO) | Demo plan | Tier 1 as written |
| OD-02 | Legal review of employee screen monitoring for the pilot company's country: notice text, consent, who may view, retention | CEO + legal adviser | TASK-018 (live viewing for real employees) | `live_view_enabled = false`; staff demo accounts only |
| OD-03 | Extension distribution: Chrome Web Store listing or managed force-install by each customer | CEO + Andleeb | TASK-019 | Unpacked extension for development and staff demo |
| OD-04 | CI/CD tool, AWS account and repository owner (report open decision) | Abiha + Subhan | Production deploy | GitHub Actions + AWS reference in Section 35 |
| OD-05 | Lead Hunter outreach beyond drafts: automatic sending, sequences, any LinkedIn or search sourcing; anti-spam review for target countries | CEO + Zareen (research) | Release 2 outreach | Drafts only, user-supplied domains only |
| OD-06 | Optional language-model provider, monthly cost cap and data agreement | CEO + Wajiha | TASK-021 | Disabled |
| OD-07 | Create the Google OAuth client and consent screen for the EMS domain | Abiha | TASK-004 step 7 (live Google test) | Email + password only; Google button shows "unavailable" |
| OD-08 | Start and end dates, team availability, stand-up schedule, QA/dev split (report open decision) | Subhan (PMO) | Schedule | No dates in this document |
| OD-09 | Transactional email provider (invites, password reset, notifications) | CEO + Abiha | TASK-020 | Copyable links; reset via company admin |

# Appendix D - Integration Register

| ID | Integration | Status | Evidence | What remains |
|---|---|---|---|---|
| INT-001 | Google sign-in (OpenID Connect) | READY TO IMPLEMENT | EV-006, EV-007 (documented) | Live test after OD-07 |
| INT-002 | LiveKit server (self-hosted) + livekit-api / livekit-client | READY TO IMPLEMENT | EV-004 (token grants locally checked), EV-005, EV-010 | Server deployment and a two-browser media test in TASK-011 |
| INT-003 | Transactional email | BLOCKED | No provider chosen (OD-09) | Choose provider, then document its API with evidence |
| INT-004 | Chrome extension platform (idle, offscreen, desktop capture, getDisplayMedia, Web Store) | READY TO IMPLEMENT (unpacked); publication BLOCKED | EV-001, EV-002, EV-003, EV-008, EV-009 | Alarms period and Web Store review (OD-03) |
| INT-005 | Public company websites (crawler) | READY TO IMPLEMENT | EV-011; ROB-01..03 | Integration test TEST-004 |
| INT-006 | Language-model rephraser | BLOCKED | None by design | OD-06 |

# Appendix E - Build Tasks

Paths are proposed (no repository exists). Owners follow the report's allocation; any developer may take a task. Each task is one reviewable pull request.

### TASK-001 Repository, tooling and CI skeleton

-   **Why:** everything depends on one repository with checks that run on every change. REQ-016.
-   **Owner / depends on:** Abiha / none.
-   **Read:** Section 35, pack README.
-   **Change:** create `ems/` with the layout in Section 35; copy `engine/`, `db/`, `contracts/`, `tools/` from this pack.
-   **Implement:** Python 3.11 project with pinned FastAPI 0.143.0, uvicorn 0.54.0, SQLAlchemy 2.1.4, Alembic 1.20.0, Pydantic 2.14.0, psycopg[binary] 3.3.6, argon2-cffi 25.1.0, httpx 0.28.1, apscheduler 3.11.3, beautifulsoup4 4.15.0, livekit-api 1.2.1, PyJWT 2.15.1; Next.js 16.4.0 app; CI job with a PostgreSQL 17 service.
-   **Run:** `python -m unittest engine.tests.test_engine` (from `backend/app`), `python tools/check_spec.py`, `python tools/check_livekit_tokens.py`.
-   **Expect:** 21 tests OK; CHK-01..12 PASS; LK-01..03 PASS.
-   **Failure checks:** `ModuleNotFoundError: engine` -> run from the folder that contains `engine/`; do not use `python -I` for project code.
-   **Done when:** CI is green on an empty pull request and the three commands pass.

### TASK-002 Database migration 0001

-   **Why:** the schema is the canonical contract for tenancy and invariants (Section 8).
-   **Depends on:** TASK-001.
-   **Read:** `db/001_ems_schema.sql`, `db/002_ems_settings_tokens.sql`, `db/verify_ems_db.py`.
-   **Implement:** Alembic revision 0001 that executes both SQL files verbatim with `op.execute(open(...).read())`; SQLAlchemy models mirror columns (no `create_all`).
-   **Run:** `psql "$ADMIN_DATABASE_URL" -v ON_ERROR_STOP=1 -f db/001_ems_schema.sql -f db/002_ems_settings_tokens.sql`, then `python db/verify_ems_db.py`.
-   **Expect:** 18 rows, all PASS.
-   **Failure checks:** `permission denied to create extension` -> run as an admin role; 002 resets the role itself. On RDS, `btree_gist` and `pg_trgm` must be allowed extensions.
-   **Done when:** DB-01..18 pass in CI on PostgreSQL 17.

### TASK-003 Request pipeline and platform services

-   **Why:** one place for sessions, organization context, permissions, envelope, errors, idempotency, audit and outbox. REQ-001, REQ-003.
-   **Depends on:** TASK-002.
-   **Read:** Sections 7, 19, 32, 33; API-001, API-009.
-   **Implement:** FastAPI dependencies `current_session`, `org_context` (opens the transaction and calls `set_config` - Section 7.1), `require(permission)`; exception handler that maps domain errors to Section 33; idempotency middleware using `idempotency_keys`; `audit()` and `emit()` helpers writing in the same transaction.
-   **Run:** pytest contract tests for API-001 and API-009 using `contracts/api-examples.json`.
-   **Expect:** responses match the examples' status codes and envelope keys.
-   **Failure checks:** zero rows everywhere -> `set_config` not called in the same transaction; cross-company rows -> connecting as `ems_owner` instead of `ems_app`.
-   **Done when:** a test proves a request with company A's session cannot read company B's member list.

### TASK-004 Authentication and onboarding

-   **Depends on:** TASK-003. **APIs:** API-002..API-008, API-010..API-012. REQ-001, REQ-002.
-   **Implement:** signup via `ems.signup_company`; login with dummy argon2 verify for unknown emails; logout; reset via `ems.create_password_reset` / `ems.consume_password_reset` (returns 202 always); Google start/callback per Section 7.3 using httpx and PyJWT with Google's JWKS; company setup; invitations with copy links while `EMAIL_PROVIDER=none`; accept via `ems.accept_invitation`.
-   **Step 7 (needs OD-07):** sign in with a real Google test account on beta.
-   **Expect:** examples API-002..012 reproduced; DB-05 and DB-16 still pass.
-   **Failure checks:** Google `aud` mismatch -> wrong client ID per environment; invite accepted twice -> token not hashed with SHA-256 consistently.
-   **Done when:** Section 2.2 steps 1-2 work in the browser.

### TASK-005 Members and roles

-   **Depends on:** TASK-004. **APIs:** API-013..API-016. REQ-003.
-   **Implement:** matrix from Section 7.2 as a Python dict used by `require()` and returned by API-016; deactivation closes the open work session and revokes extension tokens.
-   **Expect:** CEO role change refused with `ONE_CEO_ONLY`; cost rates hidden from non-finance roles.
-   **Done when:** a test per role proves allowed and denied routes.

### TASK-006 Worker, scheduler and notifications

-   **Depends on:** TASK-003. **APIs:** API-069, API-070. REQ-015.
-   **Implement:** `worker/main.py` loop: select unpublished outbox rows (worker policy, DB-14), set org context per row, call handlers, mark published; APScheduler jobs per company time zone (01:00 leakage, 23:30 HR report, hourly task.overdue, every minute presence timeout and session auto-close).
-   **Failure checks:** handler raises -> row stays unpublished and is retried with back-off; a poison row after 10 attempts is logged and skipped.
-   **Done when:** `member.invited` produces a notification within 2 seconds.

### TASK-007 Employee Room server

-   **Depends on:** TASK-005, TASK-006. **APIs:** API-017..API-023, API-025, API-028. REQ-004.
-   **Implement:** Section 9.2-9.3 with `engine/presence.py`; lateness from Section 10; extension tokens in `extension_tokens`; Room time entries at check-out.
-   **Expect:** API-020 totals for the fixture: active 412, idle 38, on_break 45, offline 48 (543 minutes, 09:02-18:05).
-   **Failure checks:** two sessions open -> missing unique index (DB-06); presence never offline -> the every-minute timeout job is not running.
-   **Done when:** TEST-006 check-in part passes (20 parallel check-ins, one session).

### TASK-008 People, HR and HR Agent

-   **Depends on:** TASK-007. **APIs:** API-029..API-037. REQ-006, REQ-007.
-   **Implement:** Section 10 rules; implement the `Repo` interface of `engine/hr_agent.py` with SQL queries; policies are inserts only (DB-18).
-   **Expect:** AGT-01..05 still pass; API-035 examples reproduced.
-   **Done when:** HR can answer the six supported questions on the fixture.

### TASK-009 Projects, tasks and time

-   **Depends on:** TASK-005. **APIs:** API-038..API-044. REQ-008.
-   **Implement:** Section 12; transitions table as code; overlap check against work sessions for manual time.
-   **Done when:** board moves with stale versions return 409 and the board reloads.

### TASK-010 CRM and client lifecycle

-   **Depends on:** TASK-009. **APIs:** API-045..API-054. REQ-009.
-   **Implement:** Section 13; Win in one transaction (deal, client, project from template, contact stage, graph edges, outbox); contact search with the trigram index from 002.
-   **Expect:** replaying API-051 with the same Idempotency-Key returns the same client; DB-09 holds.
-   **Done when:** Section 2.2 step 5 works and TEST-006 Win part passes.

### TASK-011 Chrome extension and live media

-   **Owner:** Andleeb (extension) + Abiha (API). **Depends on:** TASK-007. **APIs:** API-024, API-026, API-027. REQ-004, REQ-005.
-   **Implement:** Section 9.4-9.6. Steps: (1) manifest and popup; (2) consent and check-in; (3) heartbeats; (4) deploy LiveKit on a test host following its official deployment guide (inspect and record the guide's ports and version in Appendix G before deploying); (5) Media Session Page with `getDisplayMedia` + livekit-client 2.22.4 publish; viewer page with @livekit/components-react 2.9.24; (6) optional spike: offscreen document capture - record the result, do not ship without a passing test.
-   **Before step 3:** inspect the Chrome `alarms` reference for the minimum period; if under 30 s is not allowed, send heartbeats from the Media Session Page.
-   **Expect:** two Chrome profiles (staff test accounts): employee shares, CEO views within 5 seconds, employee sees the notice (TEST-003).
-   **Failure checks:** `NotAllowedError` -> `getDisplayMedia` not called from the click handler; black video -> picker cancelled; viewer sees nothing -> wrong room name (must be `ems-<org>-<user>`).
-   **Done when:** G4 and G5 pass with staff accounts. Real employees stay off until TASK-018.

### TASK-012 Lead Hunter crawler

-   **Owner:** Wajiha. **Depends on:** TASK-006, TASK-010. **APIs:** API-055..API-060. REQ-010.
-   **Implement:** Section 14 in the worker with httpx (timeouts, size cap) + beautifulsoup4; `engine/robots.py` and `engine/scoring.py`; crawl log row for every fetch decision.
-   **Expect:** TEST-004 against a local test server with a 503 robots.txt, a disallowed path and a 1 MB page.
-   **Done when:** a 3-domain hunt completes and promotes one prospect to CRM.

### TASK-013 Rule engine service

-   **Owner:** Wajiha. **Depends on:** TASK-006. **APIs:** API-061..API-064. REQ-011.
-   **Implement:** store rules, call `engine/rules.py` from event handlers, execute actions through module services, record `rule_runs`, chain depth limit 3; seed the starter rules in Section 15.
-   **Done when:** the stale-deal rule creates one task for the fixture and a replayed event creates none.

### TASK-014 Graph memory

-   **Depends on:** TASK-010. **API:** API-068. REQ-012.
-   **Implement:** edge writers in the event handlers listed in Section 16; close and reopen edges on change.
-   **Done when:** API-047 `related` and API-068 match the examples on the fixture; DB-11 still passes.

### TASK-015 Leakage engine and dashboards

-   **Depends on:** TASK-008, TASK-010, TASK-013. **APIs:** API-065..API-067. REQ-013, REQ-014.
-   **Implement:** nightly job feeding `engine/leakage.py` from SQL; upsert by fingerprint; auto-resolve; dashboard queries per Section 18 with 5-minute cache in PostgreSQL.
-   **Expect:** TEST-005: three findings totalling $8,620.00.
-   **Done when:** CFO dashboard has no unsourced tile.

### TASK-016 Web application screens

-   **Owner:** Andleeb with Sawera's designs. **Depends on:** each API task it uses.
-   **Implement:** the report's 45 screens in Tier order (Section 5) against the real API; six dashboard variants; empty, loading, error and unavailable states for each.
-   **Done when:** every screen in Tier 1 uses the real API and no screen shows hard-coded sample numbers.

### TASK-017 Retention, hardening and release gates

-   **Owner:** Rabia (QA) + Abiha. **Depends on:** TASK-001..TASK-016.
-   **Implement:** retention job (Section 32), security headers, rate limits, TEST-001..TEST-007.
-   **Done when:** Section 36 gates G1..G10 all PASS on beta.

### TASK-018 Enable live viewing for a real company (BLOCKED by OD-02)

-   Switch `live_view_enabled` on per company only after the legal review is recorded and G4/G5 pass.

### TASK-019 Publish the extension (BLOCKED by OD-03)

-   Prepare the store listing and privacy disclosure from Section 9.1, or the managed-install guide.

### TASK-020 Email adapter (BLOCKED by OD-09 / INT-003)

-   Implement `EmailSender.send(template, to, data)` for the chosen provider after its documentation is recorded as evidence; until then `EMAIL_PROVIDER=none`.

### TASK-021 Language-model rephraser (BLOCKED by OD-06 / INT-006)

-   Interface only exists in Release 1 (Section 20).

# Appendix F - Coding-Agent Handoff

Give any AI coding tool this text with the files it names:

    You are implementing one task of EMS Release 1.
    Read first: spec/EMS_R1_Implementation_Spec_v1.0.md (sections named in the task), the task card in
    Appendix E, db/001_ems_schema.sql, db/002_ems_settings_tokens.sql, contracts/api-examples.json, and the
    repository's own README/CONTRIBUTING if present.
    Rules:
    1. Implement only the selected task. Do not change unrelated files.
    2. Check installed package versions against Section 6.2 before using an example.
    3. Contracts are binding: status codes, error codes and JSON keys must match api-examples.json.
       If the repository conflicts with the spec, stop and report the conflict; do not invent new endpoints.
    4. Never fake an integration. If a provider (email, LLM, Google credentials) is missing, return the
       documented error (GOOGLE_NOT_CONFIGURED, copy links, AI disabled) - never a success.
    5. Keep RLS: connect as ems_app and call set_config('app.org_id', ..., true) in every transaction.
    6. Run the task's commands. Report what passed, what failed and what you could not run.
    7. Finish with: files changed, migrations, commands run with results, open blockers, next task ID.

# Appendix G - Evidence Ledger

All sources inspected on 10 October 2026 unless stated. "Documented" means read in official documentation; "locally checked" means executed in the audit sandbox.

| ID | Claim | Source | Level | If wrong |
|---|---|---|---|---|
| EV-001 | `getDisplayMedia()` needs transient user activation; permission "cannot be persisted"; the user is prompted every time; HTTPS only | https://developer.mozilla.org/en-US/docs/Web/API/MediaDevices/getDisplayMedia | documented | Media Session Page flow changes |
| EV-002 | Offscreen documents: reasons include DISPLAY_MEDIA, USER_MEDIA, WEB_RTC; Chrome 109+, MV3; one open per extension | https://developer.chrome.com/docs/extensions/reference/api/offscreen | documented | Spike in TASK-011 step 6 only |
| EV-003 | `chrome.idle`: states active, idle, locked; `queryState(seconds)`; default interval 60 s; needs "idle" permission | https://developer.chrome.com/docs/extensions/reference/api/idle | documented | Presence mapping |
| EV-004 | livekit-api 1.2.1 `AccessToken` + `VideoGrants` produce the publish/view grants in Section 9; default TTL 6 h and `canPublishData: true`, so EMS sets both | tools/check_livekit_tokens.py, LK-01..03 | locally checked | Token code |
| EV-005 | LiveKit grants: roomJoin, room, canPublish, canSubscribe, canPublishSources (camera, microphone, screen_share, screen_share_audio), canPublishData, hidden | https://docs.livekit.io/frontends/reference/tokens-grants/ | documented | Grant names |
| EV-006 | Google discovery: issuer https://accounts.google.com; authorization https://accounts.google.com/o/oauth2/v2/auth; token https://oauth2.googleapis.com/token; jwks https://www.googleapis.com/oauth2/v3/certs; PKCE plain and S256; RS256 | https://accounts.google.com/.well-known/openid-configuration | documented | Google flow |
| EV-007 | Validate signature, iss (two values), aud, exp; hd when restricting domains; use `sub` not email; state and nonce | https://developers.google.com/identity/openid-connect/openid-connect | documented | Account takeover risk |
| EV-008 | `chrome.desktopCapture.chooseDesktopMedia` always shows a picker; stream IDs are single-use and expire in seconds; permission `desktopCapture` | https://developer.chrome.com/docs/extensions/reference/api/desktopCapture | documented | Alternative capture path |
| EV-009 | Web Store: spyware prohibited; browsing activity collection prohibited except for a disclosed user-facing feature; prominent disclosure and affirmative consent; limited use. No enterprise exception found on that page | https://developer.chrome.com/docs/webstore/program-policies/policies | documented | OD-03 |
| EV-010 | LiveKit server is Apache License 2.0 and self-hostable (binary, Docker, Kubernetes) | https://github.com/livekit/livekit | documented | Media server choice |
| EV-011 | RFC 9309: most specific match; allow wins equivalent rules; 4xx -> may access; 5xx -> complete disallow; parse at least 500 KiB; cache at most 24 h | https://www.rfc-editor.org/rfc/rfc9309.html | documented | Crawler rules |
| EV-012 | PostgreSQL: owners bypass RLS unless FORCE; BYPASSRLS and superusers always bypass; no policy = default deny | https://www.postgresql.org/docs/17/ddl-rowsecurity.html | documented | Isolation design |
| EV-013 | Versions: fastapi 0.143.0, SQLAlchemy 2.1.4, pydantic 2.14.0, psycopg 3.3.6, livekit-api 1.2.1, PyJWT 2.15.1 installed; uvicorn 0.54.0, alembic 1.20.0, argon2-cffi 25.1.0, httpx 0.28.1, apscheduler 3.11.3, beautifulsoup4 4.15.0 latest on PyPI; npm next 16.4.0, livekit-client 2.22.4, @livekit/components-react 2.9.24 | `pip list`, `pip index versions`, `npm view` in the sandbox | locally checked (registry lookup, not a full app build) | Pins in TASK-001 |
| EV-014 | Schema applies and DB-01..18 pass | db/verify_ems_db.py on PostgreSQL 16.13 | locally checked | Isolation and invariants |
| EV-015 | Engine: 21 tests pass (RUL, PRS, LEK, ROB, SCO, AGT) | engine/tests/test_engine.py on Python 3.11.15 | locally checked | Rule, presence, leakage, crawler, agent logic |

Known gaps (not inspected; tasks must inspect before relying on them): Chrome `alarms` minimum period (TASK-011), LiveKit server deployment ports and current server version (TASK-011 step 4), AWS RDS PostgreSQL 17 extension list for `btree_gist` and `pg_trgm` (TASK-002), any email provider (OD-09).

# Appendix H - Verification Report

| Check | What it proves | Result |
|---|---|---|
| DB-01..DB-18 | RLS isolation, bootstrap functions, sessions, invitations, one open session under concurrency, one CEO, leave overlap, deal/client rules, project billing rules, graph isolation, dedupe, immutability, worker scan, role ownership, password reset, extension tokens, HR policy versioning | 18/18 PASS on PostgreSQL 16.13 (sandbox). Not yet run on PostgreSQL 17 or RDS |
| Engine tests | Rule validation and evaluation, presence segments, six leakage detectors, robots.txt matching, scoring, HR Agent routing and permissions | 21/21 PASS, Python 3.11.15 |
| LK-01..LK-03 | LiveKit publish and view grants and TTLs EMS issues | 3/3 PASS, livekit-api 1.2.1 (no media server involved) |
| CHK-01..CHK-12 | Specification consistency: JSON parses, references resolve, counts agree, timestamps ordered, enums match the schema, error codes catalogued, statuses listed, envelopes valid | See `tools/check_spec.py` output in the pack README |
| Junior-developer walkthrough | TASK-001 -> TASK-017 can start from an empty repository with only this pack; every task names files, commands and done criteria | Reviewed by the author (simulated, not executed) |
| Failure-path review | Concurrency (check-in, Win, payments), authorization per role, provider outages (LiveKit, Google, email), stale versions | Reviewed by the author; DB-level parts executed (DB-06, DB-09) |
| Not run | The API, web app, extension, LiveKit media, Google sign-in, crawler against real sites, AWS deployment | Not built yet - no claim is made |
