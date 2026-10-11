import { Navigate } from 'react-router-dom';
import { AuthCardShell } from '@/components/layout/AuthCardShell';
import { EnvelopeIllustration } from '@/components/ui/Illustrations';
import { ForgotPasswordForm } from '@/features/auth/ForgotPasswordForm';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** EMS_Screen_03_Forgot_Password: centered card with envelope illustration. */
export function ForgotPasswordPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <AuthCardShell
      title="Forgot your password?"
      description="No worries. Enter your work email and we'll send you a secure link to reset your password."
      footer={<>© 2026 EMS Workspace</>}
    >
      <div aria-hidden="true" className="mx-auto mb-5 flex size-20 items-center justify-center rounded-full bg-accent-soft/60 text-accent">
        <EnvelopeIllustration className="size-10" />
      </div>
      <ForgotPasswordForm />
    </AuthCardShell>
  );
}
