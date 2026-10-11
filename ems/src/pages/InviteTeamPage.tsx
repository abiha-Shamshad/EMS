import { Navigate } from 'react-router-dom';
import { OnboardingShell, OnboardingSteps } from '@/components/layout/OnboardingShell';
import { InviteAside, InviteTeamForm } from '@/features/onboarding/InviteTeamForm';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** EMS_Screen_06_Invite (step 3 of 3). */
export function InviteTeamPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <OnboardingShell
      step={<OnboardingSteps current={3} />}
      heading="Invite your team"
      subheading="Bring your colleagues into EMS so you can start working together."
      aside={<InviteAside />}
    >
      <InviteTeamForm />
    </OnboardingShell>
  );
}
