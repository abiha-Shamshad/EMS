# EMS web app (Release 1)

Next.js 16.4 (App Router) + TypeScript, as the spec requires (Frontend row, TASK-016). Every screen uses the real API;
no screen shows sample numbers. Metrics EMS cannot source are listed under "Not available yet" with the reason.

## Run

```bash
npm ci
EMS_API_ORIGIN=http://127.0.0.1:8000 npm run dev      # http://localhost:3000; /api/v1/* is proxied to the API
npm run lint && npm run typecheck && npm test && npm run build
```

The browser only talks to this origin: `next.config.ts` rewrites `/api/v1/*` to `EMS_API_ORIGIN` (read at build time), so
the session and CSRF cookies are first-party and the Chrome extension shares the same sign-in. Set the API's
`APP_BASE_URL` to this app's URL.

## Screens

| Route | Screen (designer bundle number) | API |
|---|---|---|
| `/login`, `/signup`, `/forgot-password`, `/reset-password` | 01-04 | 002-007 |
| `/invite/accept`, `/select-company`, `/no-company` | invitation link, company picker | 012, 009 |
| `/setup/company`, `/setup/invite` | 05, 06 | 010, 011 |
| `/dashboards/[role]` | 07-12, role based: each person sees only their own role's dashboard, with role shortcuts | 067 |
| `/notifications`, `/profile` | 13, 14 | 069/070, 009 |
| `/room`, `/room/view/[viewId]` | 15 (+17 offline state), 16 (live webcam and screen via LiveKit) | 025-027 |
| `/room/wall` | CEO video wall: every live employee as a grid | view-grid, 027 |
| `/room/me` | My workday: check in / check out, today, breaks, consent (with webcam opt-in), who viewed me | 017, 018, 020, 023, 028, 030 |
| `/hr`, `/hr/employees(/[id])`, `/hr/attendance`, `/hr/breaks` | 24, 25, 26, 29 | 029, 030, 034, 022 |
| `/leave`, `/leave/approvals` | 27, 28 | 031-033 |
| `/hr/agent`, `/hr/reports`, `/hr/policies` | 30, 31, 32 | 035, 034, 036/037 |
| `/projects`, `/projects/[id]` (task drawer) | 33, 34, 35 | 038-044 |
| `/crm`, `/crm/contacts(/[id])`, `/crm/pipeline`, `/crm/deals`, `/crm/clients` | 36-39, deal and client lists | 045-052, `GET /deals`, `/clients` |
| `/hunter`, `/hunter/new`, `/hunter/[id]` | 40-43 | 055-060 |
| `/automation`, `/automation/new`, `/automation/logs` | 44, 45 | 061-064 |
| `/leakage`, `/finance/invoices` | revenue leakage, invoices and payments | 065/066, 053/054 |
| `/admin/members`, `/admin/permissions`, `/admin/company` | 47, 48, company settings | 013-016, 010 |
| 404 page and "no access" blocks; confirmation dialogs | 49, 50 | - |

Not built, because the spec leaves them out of Release 1 or they would break its rules (Section 2.3): recording
history, multi-monitor view, payroll, external API keys, LinkedIn sources, email
sequences/campaigns, Gantt, client workflow builder, custom roles, audit log screen, subscription billing.

## Conventions

- `src/lib/api.ts`: envelope, `ApiError` (code, fields), CSRF header on writes, `Idempotency-Key` per form submit, `X-Org-Id`.
- `src/lib/useApi.ts`: `useApi` / `usePost` / `usePoll`; state changes only in request callbacks (React 19 lint rules).
- Money stays a decimal string (`money`, `sumMoney` use integer cents); dates are shown in the company time zone.
- Permissions come from `/me` and follow the spec Section 7.2 matrix: the sidebar, every page (a "no access" block) and every action button show only what the signed-in role may do, and the API enforces it anyway. Managers open the employee dashboard data with their own team heading and shortcuts.
