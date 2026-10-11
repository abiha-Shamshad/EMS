import type { ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';

/** Simple page for screens that are built later (design not shared yet). */
export function PlaceholderPage({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 bg-canvas px-6 text-center">
      <BrandLogo showTagline={false} />
      <h1 className="text-[32px] font-bold tracking-[-0.02em] text-ink">{title}</h1>
      {children && <p className="max-w-md text-sm text-ink-body">{children}</p>}
      <Link to="/login" className="text-sm font-semibold text-accent hover:underline">
        Back to sign in
      </Link>
    </main>
  );
}
