import { Link } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';

/** Shared shell for two-column onboarding screens (register, company setup, invite). */
export function OnboardingShell({
  step,
  heading,
  subheading,
  children,
  aside,
}: {
  step?: React.ReactNode;
  heading: string;
  subheading: string;
  children: React.ReactNode;
  aside: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-panel-from via-panel-via to-panel-to">
      <div aria-hidden="true" className="absolute -top-28 -left-28 size-[300px] rounded-full bg-accent-soft/60" />
      <div aria-hidden="true" className="absolute -right-28 -bottom-28 top-auto size-[340px] rounded-full bg-mint/60" />

      <div className="relative mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 sm:px-8">
        <div className="flex items-center justify-between gap-4">
          <BrandLogo />
          <p className="hidden text-[13px] text-ink-body sm:block">
            Need help?{' '}
            <a href="mailto:support@ems.example" className="font-bold text-accent hover:underline">
              Contact support
            </a>
          </p>
        </div>

        <main className="flex flex-1 flex-col py-8">
          {step}
          <div className="mt-2">
            <p className="text-[11px] font-bold tracking-[0.08em] text-accent uppercase">Company onboarding</p>
            <h1 className="mt-1 text-[26px] font-extrabold tracking-tight text-ink sm:text-[30px]">{heading}</h1>
            <p className="mt-1 max-w-xl text-sm text-ink-body">{subheading}</p>
          </div>
          <div className="mt-6 grid flex-1 gap-5 lg:grid-cols-[1fr_320px]">
            <div className="rounded-3xl border border-line-soft bg-white p-6 shadow-card sm:p-8">{children}</div>
            <div className="rounded-3xl border border-line-soft bg-white p-6 shadow-card sm:p-7">{aside}</div>
          </div>
          <p className="mt-6 text-center text-xs text-ink-muted">©2026 EMS — Employee Management System</p>
          <p className="mt-4 text-center sm:hidden">
            <Link to="/login" className="text-[13px] font-semibold text-accent hover:underline">
              Need help? Contact support
            </Link>
          </p>
        </main>
      </div>
    </div>
  );
}

/** Stepper shown on company-setup (step 2) and invite (step 3). */
export function OnboardingSteps({ current }: { current: 2 | 3 }) {
  const steps = [
    { n: 1, label: 'Account', state: 'Completed' },
    { n: 2, label: 'Company setup', state: current === 2 ? 'In progress' : 'Completed' },
    { n: 3, label: 'Invite team', state: current === 3 ? 'In progress' : 'Next step' },
  ];
  return (
    <div className="rounded-2xl border border-line-soft bg-white px-5 py-4 shadow-card">
      <div className="flex items-center justify-between gap-2">
        <ol className="flex flex-1 items-center gap-1 sm:gap-2" aria-label="Onboarding progress">
          {steps.map((step, index) => {
            const done = step.state === 'Completed';
            const active = step.state === 'In progress';
            return (
              <li key={step.n} className="flex flex-1 items-center gap-1 sm:gap-3" aria-current={active ? 'step' : undefined}>
                {index > 0 && <span aria-hidden="true" className="mx-1 h-px flex-1 bg-line sm:mx-2" />}
                <span
                  aria-hidden="true"
                  className={`flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-bold ${
                    done ? 'bg-primary text-white' : active ? 'bg-primary text-white' : 'bg-search-bg text-ink-muted'
                  }`}
                >
                  {done ? '✓' : step.n}
                </span>
                <span className="hidden min-w-0 sm:block">
                  <span className="block truncate text-[13px] font-bold text-ink">{step.label}</span>
                  <span className={`block text-[11px] ${active ? 'font-semibold text-primary' : 'text-ink-muted'}`}>
                    {step.state}
                  </span>
                </span>
                <span className="sm:hidden">
                  <span className="sr-only">{step.label}: {step.state}</span>
                </span>
              </li>
            );
          })}
        </ol>
        <p className="ml-2 shrink-0 text-xs font-semibold text-ink">Step {current} of 3</p>
      </div>
    </div>
  );
}
