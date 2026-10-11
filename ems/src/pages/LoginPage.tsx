import { Navigate } from 'react-router-dom';
import shieldIcon from '@/assets/icons/shield-check.svg';
import { BrandLogo } from '@/components/BrandLogo';
import { LoginForm } from '@/features/auth/LoginForm';
import { LoginHero } from '@/features/auth/LoginHero';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

export function LoginPage() {
  const session = getSession();
  if (session) return <Navigate to={dashboardPathForRole(session.user.role)} replace />;

  return (
    <div className="grid min-h-screen grid-cols-1 bg-canvas lg:grid-cols-[48fr_52fr]">
      <LoginHero />
      <main className="flex min-h-screen flex-col px-6 pt-10 sm:px-12 lg:pt-[clamp(48px,13.3vh,136px)] xl:pr-[116px] xl:pl-[89px]">
        <div className="mb-8 lg:hidden">
          <BrandLogo showTagline={false} />
        </div>
        <div className="mx-auto w-full max-w-[546px] xl:mx-0">
          <LoginForm />
        </div>
        <footer className="mx-auto mt-auto w-full max-w-[546px] pt-10 pb-8 xl:mx-0 xl:pb-[clamp(24px,11vh,112px)]">
          <p className="flex items-center gap-2 text-xs text-ink-body">
            <img src={shieldIcon} alt="" aria-hidden="true" className="size-6" />
            Secure access for your organization
          </p>
        </footer>
      </main>
    </div>
  );
}
