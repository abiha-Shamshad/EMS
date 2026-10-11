import { Navigate } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';
import { RegisterForm } from '@/features/auth/RegisterForm';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** EMS_Screen_02_Create_Company_Account: two-column register with hero panel. */
export function RegisterPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-panel-from via-panel-via to-panel-to">
      <div aria-hidden="true" className="absolute -top-28 -left-28 size-[300px] rounded-full bg-accent-soft/60" />
      <div aria-hidden="true" className="absolute -right-24 -bottom-24 size-[320px] rounded-full bg-mint/60" />

      <div className="relative mx-auto w-full max-w-6xl px-5 py-6 sm:px-8">
        <BrandLogo />
        <main className="mx-auto mt-6 grid max-w-5xl gap-0 overflow-hidden rounded-3xl border border-line-soft bg-white shadow-card lg:grid-cols-2">
          <section className="relative hidden flex-col justify-between overflow-hidden bg-white p-8 sm:p-10 lg:flex lg:border-r lg:border-line-soft/70" aria-label="Why EMS">
            <div>
              <p className="inline-flex w-fit items-center gap-1.5 rounded-full bg-accent-soft px-3 py-1 text-[11px] font-bold tracking-[0.06em] text-accent uppercase">
                <span aria-hidden="true" className="size-1.5 rounded-full bg-accent" />
                Get started
              </p>
              <h1 className="mt-4 text-[32px] leading-[1.15] font-extrabold tracking-tight text-ink sm:text-[34px]">
                Bring your
                <br />
                <span className="text-primary">team into focus.</span>
              </h1>
              <p className="mt-3 max-w-[340px] text-sm leading-6 text-ink-body">
                Set up your company workspace to organize people, projects, leads and daily operations.
              </p>

              <ul className="mt-8 space-y-5">
                <li className="flex items-start gap-3.5">
                  <span aria-hidden="true" className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#f3f0ff] text-[#7c3aed]">
                    <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M13.5 16.5v-1.5a3 3 0 0 0-3-3h-3a3 3 0 0 0-3 3v1.5" />
                      <circle cx="7.5" cy="6.5" r="3" />
                      <path d="M16.5 16.5v-1a2.5 2.5 0 0 0-2-2.45" />
                      <path d="M13.5 4.15a2.5 2.5 0 0 1 0 4.7" />
                    </svg>
                  </span>
                  <div>
                    <p className="text-sm font-bold text-ink">One team directory</p>
                    <p className="text-[13px] text-ink-muted">Keep people and roles organized.</p>
                  </div>
                </li>

                <li className="flex items-start gap-3.5">
                  <span aria-hidden="true" className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#e6fffa] text-[#0d9488]">
                    <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11.5 2.5H5.5a1.5 1.5 0 0 0-1.5 1.5v12a1.5 1.5 0 0 0 1.5 1.5h9a1.5 1.5 0 0 0 1.5-1.5V7L11.5 2.5Z" />
                      <polyline points="11.5 2.5 11.5 7 16 7" />
                      <line x1="7.5" y1="10.5" x2="12.5" y2="10.5" />
                      <line x1="7.5" y1="13.5" x2="10.5" y2="13.5" />
                    </svg>
                  </span>
                  <div>
                    <p className="text-sm font-bold text-ink">Work in one place</p>
                    <p className="text-[13px] text-ink-muted">Connect tasks, CRM and HR workflows.</p>
                  </div>
                </li>

                <li className="flex items-start gap-3.5">
                  <span aria-hidden="true" className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[#fff7ed] text-[#ea580c]">
                    <svg viewBox="0 0 20 20" className="size-5" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
                      <path d="M10 2.5 4 5v5c0 4.5 2.5 7.5 6 8.5 3.5-1 6-4 6-8.5V5l-6-2.5Z" />
                      <polyline points="7.5 10 9.2 11.7 12.5 8.3" />
                    </svg>
                  </span>
                  <div>
                    <p className="text-sm font-bold text-ink">Your workspace, your rules</p>
                    <p className="text-[13px] text-ink-muted">Start with clear company-level access.</p>
                  </div>
                </li>
              </ul>
            </div>

            {/* Bottom illustration matching reference */}
            <div aria-hidden="true" className="relative mt-10 pt-6">
              {/* Ground shadow oval */}
              <div className="mx-auto h-5 w-4/5 rounded-[100%] bg-accent-soft/50 blur-xs" />

              {/* Plant on bottom left */}
              <div className="absolute -left-1 bottom-3 z-10 flex flex-col items-center">
                <svg viewBox="0 0 32 32" className="size-8 drop-shadow-xs" fill="none">
                  <path d="M16 18C14 11 8 6 3 6c0 6 5 11 13 12Z" fill="#10b981" />
                  <path d="M16 18c2-7 8-12 13-12 0 6-5 11-13 12Z" fill="#059669" />
                  <path d="M16 18c-1-4 0-8 1.5-11 1.5 3 1 7-1.5 11Z" fill="#34d399" />
                </svg>
                <div className="h-5 w-4.5 rounded-b-md bg-primary shadow-xs" />
              </div>

              {/* Floating team card with READY TO GO badge */}
              <div className="relative -mt-4 ml-6 rounded-2xl border border-line-soft bg-white p-3.5 shadow-card">
                {/* Dotted curve up to READY TO GO badge */}
                <svg className="pointer-events-none absolute -top-8 right-12 h-10 w-24 overflow-visible" fill="none">
                  <path d="M 0 32 C 12 16, 36 6, 68 0" stroke="#94a3b8" strokeWidth="1.5" strokeDasharray="3 3" />
                </svg>

                {/* Floating READY TO GO badge */}
                <div className="absolute -top-11 right-2 flex items-center gap-1.5 rounded-full border border-line-soft bg-white px-2.5 py-1 shadow-xs">
                  <span className="flex size-3.5 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-white">✓</span>
                  <span className="text-[10px] font-extrabold tracking-wider text-ink uppercase">Ready to go</span>
                </div>

                {/* 3 mini cards */}
                <div className="grid grid-cols-3 gap-2">
                  <div className="flex items-center gap-2 rounded-xl bg-panel-from p-2 border border-line-soft/50">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-amber-200">
                      <span className="size-2 rounded-full bg-amber-600" />
                    </span>
                    <div className="space-y-1">
                      <div className="h-1.5 w-8 rounded-full bg-primary" />
                      <div className="h-1.5 w-5 rounded-full bg-line" />
                    </div>
                  </div>

                  <div className="flex items-center gap-2 rounded-xl bg-panel-from p-2 border border-line-soft/50">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-blue-200">
                      <span className="size-2 rounded-full bg-primary" />
                    </span>
                    <div className="space-y-1">
                      <div className="h-1.5 w-8 rounded-full bg-primary" />
                      <div className="h-1.5 w-5 rounded-full bg-line" />
                    </div>
                  </div>

                  <div className="flex items-center gap-2 rounded-xl bg-panel-from p-2 border border-line-soft/50">
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full bg-emerald-100 text-[10px] font-bold text-emerald-600">
                      ✓
                    </span>
                    <div className="space-y-1">
                      <div className="h-1.5 w-8 rounded-full bg-primary" />
                      <div className="h-1.5 w-5 rounded-full bg-line" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section className="p-6 sm:p-9" aria-label="Create your company">
            <RegisterForm />
          </section>
        </main>
        <p className="mt-6 text-center text-xs text-ink-muted">©2026 EMS — Employee Management System</p>
      </div>
    </div>
  );
}
