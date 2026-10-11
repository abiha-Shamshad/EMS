# Rules for AI coding agents (Antigravity etc.) working in this repo

Read `README.md` first, then follow these project rules (from the EMS Engineering Handbook).

## Stack
TypeScript strict, React, Vite, Tailwind v4, React Router, TanStack Query. No `any` for API data.

## Golden rules
1. The backend OpenAPI contract is the source of truth. Never guess endpoints or field names; mark guesses `CONTRACT-PENDING`.
2. Shared enums only (`src/lib/enums.ts`, later generated). Never hand-type "on_break" etc. in components.
3. `company_id` comes from the token. The frontend never sends it.
4. All API calls go through `src/api/client.ts`. No raw `fetch()` in components.
5. Every data screen handles 4 states: loading, empty, error, data.
6. Colors, fonts, radii come from tokens in `src/styles/index.css`. No hex codes inside components.
7. Role-based UI uses ONE helper `can(role, permission)` in `src/lib/permissions.ts`. Dates only through `formatDateTime()` in `src/lib/datetime.ts`.

## Naming
Components/files PascalCase; hooks `useXxx`; feature folders kebab-case; TS camelCase; API JSON snake_case (do not convert);
env vars `VITE_*`; branches `feat/<card-no>-<name>`; Conventional Commits.

## Design fidelity
`design-reference/` holds the Figma screenshots. UI must match them exactly (spacing, colors, radii, copy).
All images go in `src/assets/images`, all icons in `src/assets/icons` (imported, never hot-linked) so the app works on Vercel and offline.

## Before finishing any task
`npm run lint && npm run build` must pass.
