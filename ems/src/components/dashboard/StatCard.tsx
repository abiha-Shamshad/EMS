import type { StatCardDatum } from '@/demo/fixtures';
import { Badge } from '@/components/ui/Badge';

const ICONS: Record<StatCardDatum['icon'], React.JSX.Element> = {
  people: (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true">
      <circle cx="12" cy="8" r="3.4" />
      <path d="M5.5 19.5c.9-3.4 3.4-5 6.5-5s5.6 1.6 6.5 5" />
    </svg>
  ),
  check: (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="8.5" />
      <path d="m8.5 12 2.5 2.5 4.5-5" />
    </svg>
  ),
  doc: (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true">
      <rect x="6" y="4" width="12" height="16" rx="2" />
      <path d="M9 9.5h6M9 13h6" />
    </svg>
  ),
  dollar: (
    <svg viewBox="0 0 24 24" className="size-6" fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round" aria-hidden="true">
      <path d="M12 4v16M15.5 7.5c-.7-1-2-1.5-3.5-1.5-2 0-3.4 1-3.4 2.6 0 3.5 7 1.7 7 5.4 0 1.6-1.5 2.6-3.6 2.6-1.6 0-3-.6-3.7-1.6" />
    </svg>
  ),
};

const ICON_TONES: Record<StatCardDatum['icon'], string> = {
  people: 'bg-info-bg text-info-text',
  check: 'bg-success-bg text-success-text',
  doc: 'bg-warning-bg text-warning-text',
  dollar: 'bg-purple-bg text-purple-text',
};

export function StatCard({ datum }: { datum: StatCardDatum }) {
  return (
    <article className="flex flex-col items-center rounded-card bg-card px-4 py-5 text-center shadow-card">
      <div className="flex items-center gap-2.5">
        <span aria-hidden="true" className={`flex size-11 items-center justify-center rounded-xl ${ICON_TONES[datum.icon]}`}>
          {ICONS[datum.icon]}
        </span>
        <div className="text-left">
          <h3 className="text-xs font-semibold text-ink">{datum.label}</h3>
          <p className="text-[26px] leading-7 font-extrabold tracking-tight text-ink">{datum.value}</p>
        </div>
      </div>
      <p className="mt-3 flex items-center gap-1.5 text-xs text-ink-muted">
        {datum.footBadge && (
          <Badge tone={datum.footBadgeTone === 'warning' ? 'warning' : 'success'}>{datum.footBadge}</Badge>
        )}
        {datum.footNote}
      </p>
    </article>
  );
}
