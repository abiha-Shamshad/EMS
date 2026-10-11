# EMS Dashboard (frontend)

React + Vite + TypeScript (strict) + Tailwind CSS v4 + React Router + TanStack Query.
Built by **Andleeb Zahra (frontend)** from Sawera's Figma frames in `design-reference/`
(screens 01–07) and the Release 1 Implementation Spec contracts.

## Role Dashboards & Screens

| Path | Screen & Role | Features |
|---|---|---|
| `/login` | 01 Login | Work email, password, keep me signed in, quick demo role picker |
| `/register` | 02 Create Company Account | Company name, work email, password, terms |
| `/forgot-password` | 03 Forgot Password | Work email → reset link, expiry notice |
| `/reset-password` | 04 Reset Password | Strength meter + checklist + confirm |
| `/company-setup` | 05 Company Setup | Step 2: company details form + pre-filled name |
| `/invite-team` | 06 Invite | Step 3: email + role rows, 300-char message, copy-link result |
| `/app/dashboard` | 07 CEO Dashboard | Greeting, 4 stat cards, revenue chart, workforce donut, attention + activity |
| `/app/cto-dashboard` | 08 CTO Dashboard | Engineering projects, roadmap progress, alerts, APM telemetry indicators |
| `/app/cfo-dashboard` | 09 CFO Dashboard | Revenue vs expenses comparison, budget utilization, transactions & invoices |
| `/app/coo-dashboard` | COO Dashboard | Operations, live room workforce presence, project delivery, operational events |
| `/app/hr-dashboard` | HR Dashboard | Employee directory, leave requests & approvals, rule-based HR Agent |
| `/app/manager-dashboard` | Manager Dashboard | Team sprint tasks & status advancement, team leave requests, my CRM deals |
| `/app/employee-dashboard` | Employee Workspace | Check-in/out, presence status, break timer, my tasks, who viewed my screen log |
| `/app/monitoring`, `/app/hr`, `/app/projects`, … | Workspace Modules | Connected tools & role-gated administration |

## Run

```bash
npm install
npm run dev        # http://localhost:5173
npm run build      # type-check + production build
npm run lint
npm run format
```

Demo mode (no backend needed): `VITE_DEMO_MODE=true` (already set in `.env.development`).
Any valid email + a password of 4+ characters signs you in; signup, company setup,
invites (with copyable links) and password reset all work against fictional sample data.

## Project structure

```
src/
  api/          client.ts (token + {data}/{error} envelope), errors.ts, auth.ts
  assets/
    images/     ems-logo-mark.svg, login-illustration.svg   <- all images live here
    icons/      mail, lock, eye, eye-off, check, shield, google, chip icons
  components/
    ui/         Button, TextField, Select, Textarea, Checkbox, Badge,
                Avatar, Modal, Toast, StateBlocks, Illustrations, DemoBadge
    layout/     AppShell (sidebar + drawer + topbar), Sidebar, breadcrumbs,
                AuthCardShell, OnboardingShell, icons
    dashboard/  StatCard, RevenueChart (SVG), WorkforceDonut (SVG), DashboardPanels
  features/
    auth/       LoginForm, RegisterForm, ForgotPasswordForm, ResetPasswordForm, LoginHero
    onboarding/ CompanySetupForm, InviteTeamForm
  hooks/        useLogin (TanStack Query mutation)
  lib/          env, enums (shared enums), labels, permissions (can()), session,
                validation (spec-derived rules), datetime
  demo/         fixtures.ts — fictional sample data, clearly separated
  pages/        one file per route-level screen
  routes/       guards.tsx (RequireAuth)
  styles/       index.css  <- ALL design tokens (colors, font, radius) live here
```

## Design tokens

Defined once in `src/styles/index.css` (`@theme`), taken from the Figma frames:
navy `ink`, purple `accent`, blue `primary`, `line` borders, mint/lavender panel colors, Inter font.
Components use token classes only (`bg-primary`, `text-ink`...), never hex.

## Validation rules (from the spec)

- Login: valid work email + non-empty password.
- Register: company name, valid email, password 12–128 chars (common-password block),
  terms acceptance required.
- Forgot password: valid email. Response never reveals whether the email exists.
- Reset: 8+ chars with upper, lower, number, special (live checklist + strength meter);
  confirmation must match; token single-use, 30-minute expiry.
- Company setup: name, industry, size, time zone required; website must be a valid URL.
- Invite: up to 20 rows, valid unique emails, role per row; message max 300 characters.

## Deploy to Vercel

1. Push the repo to GitHub. In Vercel: **Add New > Project**, import it.
2. Framework preset: **Vite** (build `npm run build`, output `dist`).
3. Environment variables: `VITE_API_URL` (backend URL), `VITE_DEMO_MODE`
   (`true` for a demo without backend, `false` when the API is live).
4. `vercel.json` already rewrites all routes to `index.html` so `/login`
   (and refreshed nested routes like `/app/dashboard`) work on refresh.

## Connecting the backend (later)

`src/api/auth.ts` calls the real contract paths (`/api/v1/auth/*`, `/api/v1/org`,
`/api/v1/invitations`) and maps snake_case fields at the boundary only.
After Abiha's contract PR: add `npm run gen:api` (openapi-typescript ->
`shared/api-types.ts`), replace the local shapes with the generated types,
set `VITE_DEMO_MODE=false`. Nothing else in the UI changes.
