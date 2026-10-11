import { Link, Navigate } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';
import { LockIllustration } from '@/components/ui/Illustrations';
import { ResetPasswordForm } from '@/features/auth/ResetPasswordForm';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** EMS_Screen_04_Reset_Password: hero panel left, reset card right. */
export function ResetPasswordPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-panel-from via-white to-panel-to">
      <div className="relative mx-auto grid min-h-screen w-full max-w-6xl grid-cols-1 gap-8 px-5 py-6 sm:px-8 lg:grid-cols-2 lg:items-center">
        <section aria-label="About resetting your password">
          <BrandLogo />
          <p className="mt-10 text-[11px] font-bold tracking-[0.08em] text-accent uppercase">Reset your password</p>
          <h1 className="mt-2 text-[30px] leading-tight font-extrabold tracking-tight text-ink sm:text-[36px]">
            Create a new password
          </h1>
          <p className="mt-2 max-w-[380px] text-sm leading-6 text-ink-body">
            Your new password should be strong and unique to keep your account secure.
          </p>
          <div aria-hidden="true" className="mt-8 hidden max-w-[420px] items-center justify-center rounded-3xl border border-line-soft bg-white/70 p-6 text-primary lg:flex">
            <LockIllustration className="size-24" />
          </div>
          <ul className="mt-8 grid max-w-[440px] grid-cols-1 gap-3 sm:grid-cols-3">
            {[
              { label: 'Keep your account safe & secure' },
              { label: 'Strong password protection' },
              { label: 'Quick and easy reset' },
            ].map((item) => (
              <li key={item.label} className="flex items-center gap-2 text-xs text-ink-body">
                <span aria-hidden="true" className="flex size-8 shrink-0 items-center justify-center rounded-full bg-info-bg text-primary">
                  <LockIllustration className="size-4" />
                </span>
                {item.label}
              </li>
            ))}
          </ul>
        </section>

        <main className="rounded-3xl border border-line-soft bg-white p-6 shadow-card sm:p-9" aria-label="Reset your password">
          <p className="text-right text-[13px]">
            <Link to="/login" className="font-bold text-accent hover:underline">
              ← Back to Sign In
            </Link>
          </p>
          <div aria-hidden="true" className="mt-2 flex size-12 items-center justify-center rounded-full bg-info-bg text-primary">
            <LockIllustration className="size-6" />
          </div>
          <h2 className="mt-3 text-[24px] font-extrabold tracking-tight text-ink">Reset Password</h2>
          <p className="mt-1 text-sm text-ink-body">Enter your new password below.</p>
          <div className="mt-5">
            <ResetPasswordForm />
          </div>
        </main>
      </div>
    </div>
  );
}
