import type { ReactNode } from 'react';
import { Button } from './Button';

function StateShell({ title, children, icon }: { title: string; children: ReactNode; icon: string }) {
  return (
    <div className="flex flex-col items-center gap-2 rounded-2xl border border-line-soft bg-white px-6 py-10 text-center">
      <span aria-hidden="true" className="flex size-11 items-center justify-center rounded-full bg-search-bg text-xl">
        {icon}
      </span>
      <h3 className="text-base font-bold text-ink">{title}</h3>
      <div className="max-w-sm text-sm text-ink-muted">{children}</div>
    </div>
  );
}

export function LoadingState({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-3 rounded-2xl border border-line-soft bg-white px-6 py-10">
      <span aria-hidden="true" className="size-5 animate-spin rounded-full border-2 border-line border-t-primary" />
      <p className="text-sm text-ink-muted">{label}</p>
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <StateShell title={title} icon="◌">
      {children ?? <p>Nothing to show yet.</p>}
    </StateShell>
  );
}

export function ErrorState({ title = 'Something went wrong', children, onRetry }: { title?: string; children?: ReactNode; onRetry?: () => void }) {
  return (
    <StateShell title={title} icon="!">
      {children ?? <p>Check your connection and try again.</p>}
      {onRetry && (
        <p className="mt-3 w-40">
          <Button type="button" variant="outline" onClick={onRetry}>
            Try again
          </Button>
        </p>
      )}
    </StateShell>
  );
}

export function NoAccessState({ children }: { children?: ReactNode }) {
  return (
    <StateShell title="No access" icon="🔒">
      {children ?? <p>Your role does not allow this page. Ask your company admin for access.</p>}
    </StateShell>
  );
}
