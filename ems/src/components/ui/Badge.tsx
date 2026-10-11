import type { ReactNode } from 'react';

type Tone = 'success' | 'warning' | 'info' | 'purple' | 'neutral' | 'danger';

const tones: Record<Tone, string> = {
  success: 'bg-success-bg text-success-text',
  warning: 'bg-warning-bg text-warning-text',
  info: 'bg-info-bg text-info-text',
  purple: 'bg-purple-bg text-purple-text',
  neutral: 'bg-search-bg text-ink-muted',
  danger: 'bg-danger-soft text-danger',
};

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full px-2.5 py-1 text-[11px] leading-4 font-semibold ${tones[tone]}`}
    >
      {children}
    </span>
  );
}
