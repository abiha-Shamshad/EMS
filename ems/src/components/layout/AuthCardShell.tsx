import { Link } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';

/** Shared shell for single-card auth screens (forgot password). */
export function AuthCardShell({
  eyebrow,
  title,
  description,
  children,
  footer,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}) {
  return (
    <div className="relative min-h-screen overflow-hidden bg-gradient-to-b from-panel-from via-panel-via to-panel-to">
      <div aria-hidden="true" className="absolute -top-24 -left-24 size-[280px] rounded-full bg-accent-soft/60" />
      <div aria-hidden="true" className="absolute top-10 -right-20 size-[180px] rounded-full bg-accent-soft/50" />
      <div aria-hidden="true" className="absolute -right-24 -bottom-24 size-[320px] rounded-full bg-mint/60" />

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

        <main className="flex flex-1 items-center justify-center py-10">
          <div className="w-full max-w-[460px]">
            <div className="rounded-3xl border border-line-soft bg-white px-6 py-8 shadow-card sm:px-9">
              {eyebrow && (
                <p className="mb-4 text-center text-[11px] font-bold tracking-[0.08em] text-accent uppercase">
                  {eyebrow}
                </p>
              )}
              <h1 className="text-center text-[26px] leading-8 font-extrabold tracking-tight text-ink">
                {title}
              </h1>
              {description && (
                <p className="mx-auto mt-2 max-w-[340px] text-center text-sm text-ink-body">{description}</p>
              )}
              <div className="mt-6">{children}</div>
            </div>
            {footer && (
              <div className="mt-6 text-center text-xs text-ink-muted">
                {footer}
                <p className="mt-3 flex items-center justify-center gap-2">
                  <Link to="/login" className="hover:underline">Privacy</Link>
                  <span aria-hidden="true">•</span>
                  <Link to="/login" className="hover:underline">Terms</Link>
                  <span aria-hidden="true">•</span>
                  <Link to="/login" className="hover:underline">Status</Link>
                </p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
