import { Navigate } from 'react-router-dom';
import { OnboardingShell, OnboardingSteps } from '@/components/layout/OnboardingShell';
import { FolderIllustration } from '@/components/ui/Illustrations';
import { CompanySetupForm } from '@/features/onboarding/CompanySetupForm';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** EMS_Screen_05_Company_Setup (step 2 of 3). */
export function CompanySetupPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <OnboardingShell
      step={<OnboardingSteps current={2} />}
      heading="Set up your company"
      subheading="Tell us a little about your organization to personalize your EMS workspace."
      aside={
        <div>
          <span aria-hidden="true" className="flex size-12 items-center justify-center rounded-2xl bg-info-bg text-primary">
            <FolderIllustration className="size-6" />
          </span>
          <h2 className="mt-4 text-lg font-extrabold text-ink">Your workspace, your way</h2>
          <p className="mt-1 text-[13px] text-ink-body">
            These details help EMS tailor your workspace to your organization.
          </p>
          <ul className="mt-5 space-y-3 border-t border-line-soft pt-5">
            {[
              { title: 'Personalized dashboards', text: 'Metrics relevant to your business' },
              { title: 'Smarter team setup', text: 'Configure roles and team access' },
              { title: 'One connected workspace', text: 'HR, projects, CRM and reporting' },
            ].map((item) => (
              <li key={item.title} className="flex gap-2.5">
                <span aria-hidden="true" className="mt-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-success-bg text-[11px] font-bold text-success-text">✓</span>
                <div>
                  <p className="text-[13px] font-bold text-ink">{item.title}</p>
                  <p className="text-xs text-ink-muted">{item.text}</p>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-5 rounded-2xl bg-panel-from p-4 text-xs text-ink-body">
            <span className="font-bold text-ink">Your data stays in your control.</span>
            <br />
            You can update these details later from Company Settings.
          </p>
        </div>
      }
    >
      <CompanySetupForm />
    </OnboardingShell>
  );
}
