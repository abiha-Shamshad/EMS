---
brand: "EMS"
title: "EMS - Employee Management System"
subtitle: "Idea Briefing for the Team - What We Are Building, Why, and How Each of Us Fits In"
tagline: "Read this first. The Release 1 Implementation Specification holds the exact contracts; this briefing holds the idea."
---

| Briefing item | Value |
|---|---|
| Document code | EMS-BRIEF-1.0 |
| Audience | Abiha, Andleeb, Subhan, Sawera, Wajiha, Asra, Zareen, Rabia |
| Companion document | EMS Release 1 Implementation Specification (EMS-R1-IMPL-1.0.0) |
| Status of the product | Planning complete for Release 1; nothing is built yet. Database schema and core logic engine are drafted and tested (see Section 9) |
| Date | 10 October 2026 |

::: callout-green
The idea in one sentence

EMS is the CEO's operating system: one place that shows who is working on what right now, which clients and deals need action, and where the company is losing money - and it does this with its own logic, not with paid AI calls on every click.
:::

# 1. The Problem We Solve

A growing company of 10 to 200 people usually runs on five or six tools: a task tool (like ClickUp), a CRM and marketing tool (like GoHighLevel), an HR or attendance sheet, a time tracker, spreadsheets for invoices, and chat. The CEO cannot see the whole picture, and money leaks through the gaps between the tools:

-   A developer works three hours for a client, but nobody bills it.
-   A deal is won in the CRM, but the project never starts, or nobody invoices it.
-   An invoice is two weeks overdue and nobody follows up.
-   A promising deal goes silent for three weeks.
-   Half the team is on leave in the same week and the CEO finds out on Monday.

EMS closes those gaps because people, work, clients and money live in one database and are connected.

# 2. What EMS Is - Seven Engines

| Engine | What it does | Feels like |
|---|---|---|
| 1. Work | Projects, Kanban boards, tasks, time that fills itself in from the Employee Room | ClickUp |
| 2. People and HR Agent | Directory, attendance, leave, policies; an HR Agent that answers "Who is on leave today?" from real records | An HR assistant that never guesses |
| 3. Live Employee Room | Employees check in through a Chrome extension; leadership sees who is active, idle, on break or offline, and can open a live screen view - always with notice and a log the employee can see | A transparent virtual office |
| 4. CRM and Client Lifecycle | Contacts, deals, pipeline; one "Win" button creates the client and kickoff project together | GoHighLevel's pipeline, connected to delivery |
| 5. Lead Hunter | Our own polite crawler reads company websites the user supplies, scores them against the ideal customer profile and drafts an outreach email | A research assistant for sales |
| 6. Automation and Memory | Rules like "if a deal is quiet for 14 days, create a follow-up task"; a company knowledge graph that links people, clients, projects and deals | Zapier-style rules + a memory of who-works-on-what |
| 7. Revenue and Leakage | Every night EMS finds unbilled time, overdue invoices, stale deals, won deals without a project or invoice, budget overruns - each with an amount and evidence | A CFO assistant watching for lost money |

# 3. A Day With EMS

| Time (PKT) | What happens |
|---|---|
| 09:02 | Bilal clicks Check in in the extension and picks his task "Auth API". The CEO's live grid shows him as active. |
| 09:15 | HR asks the HR Agent "Who came late today?" - "1 late on 2026-10-12 (after 10 min grace): Ayesha Noor 12 min", with links to the sessions. |
| 10:31 | Imran (CEO) opens Bilal's screen with the reason "Daily stand-up check". Bilal's extension shows "Imran Qureshi is viewing your screen". |
| 13:00 | Bilal takes a 45-minute lunch break; screen sharing pauses automatically. |
| Afternoon | Usman wins the Northwind deal. One click creates the client, the "Northwind website" project and its 12 standard tasks. |
| 18:05 | Bilal checks out. EMS turns his active time on Northwind tasks into time entries - nobody has to fill a timesheet. |
| 01:00 | The leakage engine runs: invoice INV-2026-1031 is 11 days overdue ($6,000.00), the Contoso redesign deal has been silent for 17 days ($2,500.00 weighted), and 3 hours on Contoso support are unbilled ($120.00). |
| 09:00 next day | The CEO dashboard shows "Revenue at risk: $8,620.00" with the three reasons. Omar (CFO) sends a reminder and marks the finding resolved. |

All names, companies and amounts in this briefing are invented examples.

# 4. What Makes EMS Different

1.  **One connected record.** A won deal, its client, its project, the people on it, their hours and the invoice are linked. That link is what lets EMS see leakage.
2.  **Leadership visibility with employee trust.** The live room is transparent by design: notice, consent, Chrome's own picker, and a "who viewed my screen" page the employee always sees.
3.  **Logic first, AI calls never by default.** Every automated answer comes from rules, scoring, graph queries and templates. It is fast, costs nothing per use, gives the same answer every time and can explain itself.
4.  **Money-aware.** Other tools manage work. EMS also tells the CEO how much money is at risk and why.
5.  **Honest dashboards.** A tile without a real data source says "unavailable - connect a source" instead of showing pretty sample numbers.

# 5. How "AI Without API Calls" Works

| Instead of asking an AI model... | EMS uses | Example |
|---|---|---|
| "Should I follow up this deal?" | A JSON rule the CEO can read | `deal.days_since_activity >= 14` and stage in proposal/negotiation -> notify owner + create task |
| "Who is on leave today?" | HR Agent: a question classifier + database query + answer template with sources | "1 on leave on 2026-10-12: Hina Shah (annual)" |
| "Is this company a good lead?" | Transparent scoring: industry 30, country 15, contact page 10, public email 15, team size 15, technology 15 | BrightPixel scores 85 with five listed reasons |
| "What is related to this client?" | Graph memory: nodes and edges in PostgreSQL, walked up to 3 steps | Northwind Digital -> Website rebuild deal -> Northwind website project -> Bilal Ahmed |
| "Are we losing money?" | Seven nightly detectors with fixed formulas | 180 unbilled minutes x $40.00/h = $120.00 |

A language-model adapter exists only as a switched-off interface. If we ever turn it on, it may reword an answer EMS already computed; it never decides anything.

# 6. Trust and Privacy Principles (non-negotiable)

-   The Room never records keystrokes, URLs, browsing history, webcam, microphone or screenshots, and Release 1 stores no video.
-   Screen sharing always starts with the employee's click and Chrome's picker; Chrome shows its own sharing indicator. We never try to hide it.
-   Every live view needs a reason and is shown to the employee.
-   Idle time is a conversation starter for a manager, never an automatic penalty or a performance score.
-   Live viewing of real employees stays switched off until a legal review for the customer's country is done (OD-02).
-   One company can never see another company's data - the database itself enforces this.
-   The Lead Hunter only reads websites the user supplies, obeys robots.txt, stores only public business addresses like info@, and respects opt-outs. No LinkedIn or search-engine scraping.

# 7. Release Plan

The report's plan of 45 screens with working logic in 7 days is not realistic; the report says so itself. We commit to an order and a must-work tier, and the PMO sets the dates.

| Tier | What "done" means | Modules |
|---|---|---|
| Tier 1 - must work in the demo | Real data, real API, tests pass | Sign-in and onboarding, roles, Room check-in and presence, attendance and leave, projects and Kanban, CRM pipeline with Win, leakage findings, CEO dashboard |
| Tier 2 - working, narrower | Real API, fewer screens | HR Agent, rule engine with 3 starter rules, Lead Hunter up to 50 domains, CFO and HR dashboards |
| Tier 3 - UI with clear limits | Unavailable parts labelled | CTO and COO dashboards, integration settings, live screen view on staff demo accounts |

Release 2 adds the report's Week 2 list: payroll, onboarding, recording history (only after legal review), email sync and sequences, Gantt, custom roles, audit log screen, client workflow builder and billing.

# 8. Who Owns What

| Person | Role | Release 1 ownership | First task |
|---|---|---|---|
| Abiha | Backend | Repository, database, auth, roles, Room server, HR, projects, CRM APIs | TASK-001, TASK-002, TASK-003 |
| Andleeb | Frontend | Web app screens; Chrome extension (popup, consent, Media Session Page) | TASK-016 shell, then TASK-011 |
| Sawera | UI/UX | Design system; Tier 1 screens first; six dashboard variants; empty, loading, error and "unavailable" states | Auth + CEO dashboard + Room designs |
| Wajiha | AI and automation | Rule engine service, HR Agent integration, Lead Hunter crawler and scoring, leakage job | TASK-013, TASK-012 |
| Subhan | PMO | Tier confirmation, dates, decisions log, demo plan | OD-01, OD-08 |
| Rabia | QA | Test cases from the API examples; release gates; privacy and concurrency tests | TASK-017 test plan |
| Asra | Documentation | API documentation generated from the contracts file; user guides; changelog | Guide for the extension consent notice |
| Zareen | Research and social | Legal and policy research input for OD-02 and OD-05; competitor gaps (ClickUp, GoHighLevel); launch content | OD-05 research brief |

# 9. What Exists Today

| Item | State |
|---|---|
| Implementation report (PMO) | Read and audited - 13 findings, all resolved or turned into decisions |
| Four screen designs: Login, Invite, CTO dashboard, CFO dashboard | Read; contracts follow them. CTO and CFO screens contain metrics we cannot source yet and two number mismatches - design will be updated |
| Database schema (2 SQL files) | Written and applied; 18 database checks pass in a test PostgreSQL |
| Logic engine (rules, presence, leakage, robots.txt, scoring, HR Agent) | Written in plain Python; 21 tests pass |
| API contracts | 70 operations with request, success and error examples |
| Application, web app, extension, deployment | Not built yet |

# 10. Decisions Needed From Leadership

| ID | Decision | Why it matters |
|---|---|---|
| OD-01 | Confirm the Tier 1 modules for the demo | Focus for a small team |
| OD-02 | Legal review of screen monitoring for the pilot country | Required before live viewing of real employees |
| OD-03 | Chrome Web Store listing or managed install | Store policy reviews monitoring extensions strictly |
| OD-04 | CI/CD tool, AWS account, repository owner | Needed before the first deploy |
| OD-05 | Any outreach beyond drafts; any new lead sources | Anti-spam and data-protection exposure |
| OD-06 | Whether to ever enable a language-model provider, with a cost cap | Cost and data sharing |
| OD-07 | Create the Google sign-in client | "Continue with Google" button |
| OD-08 | Dates, availability, stand-ups | Schedule |
| OD-09 | Email provider | Invitation and reset emails (until then: copy links) |

# 11. Glossary

| Term | Meaning |
|---|---|
| Organization / company | One customer of EMS; all its data is isolated from other customers |
| Work session | One check-in to check-out period |
| Presence | active, idle (no input for 5 minutes), locked, on break, offline (no heartbeat for 90 seconds) |
| Heartbeat | The extension's message every 30 seconds saying the employee is still there |
| Media Session Page | The extension tab where the employee starts screen sharing with one click |
| LiveKit | Open-source (Apache 2.0) media server we host ourselves to carry live video |
| RLS | Row-level security: PostgreSQL itself hides other companies' rows |
| Rule | A readable "when ... then ..." instruction the automation engine runs |
| Graph memory | Links between people, clients, deals and projects stored in our database |
| Leakage finding | A detected case of money at risk, with amount, evidence and status |
| ICP | Ideal customer profile used by the Lead Hunter to score prospects |
| robots.txt | A website's file saying what crawlers may read; we always obey it |
