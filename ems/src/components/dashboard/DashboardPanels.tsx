import { Link } from 'react-router-dom';
import type { ActivityItem, AttentionItem } from '@/demo/fixtures';
import { Badge } from '@/components/ui/Badge';

export function AttentionList({ items }: { items: AttentionItem[] }) {
  return (
    <section aria-labelledby="attention-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 id="attention-heading" className="text-[15px] font-bold text-ink">
            Needs your attention
          </h2>
          <p className="mt-0.5 text-xs text-ink-muted">Priority items across the organization</p>
        </div>
        <Link to="/app/hr" className="shrink-0 text-xs font-semibold text-primary hover:underline">
          View all →
        </Link>
      </div>
      <ul className="mt-4 space-y-3">
        {items.map((item) => (
          <li
            key={item.id}
            className="flex items-center gap-3 rounded-2xl border border-line-soft bg-white px-4 py-3.5"
          >
            <span
              aria-hidden="true"
              className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${
                item.tone === 'warning' ? 'bg-warning-bg text-warning-text' : 'bg-info-bg text-info-text'
              }`}
            >
              {item.tone === 'warning' ? '!' : '+'}
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-[13px] font-bold text-ink">{item.title}</p>
              <p className="truncate text-xs text-ink-muted">{item.description}</p>
            </div>
            <Badge tone={item.tone === 'warning' ? 'warning' : 'info'}>{item.badge}</Badge>
          </li>
        ))}
      </ul>
    </section>
  );
}

const ACTIVITY_TONES: Record<ActivityItem['tone'], string> = {
  blue: 'bg-chart-line',
  teal: 'bg-success',
  amber: 'bg-warning-text',
};

export function ActivityFeed({ items }: { items: ActivityItem[] }) {
  return (
    <section aria-labelledby="activity-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
      <div className="flex items-start justify-between gap-3">
        <h2 id="activity-heading" className="text-[15px] font-bold text-ink">
          Recent activity
        </h2>
        <Link to="/app/reports" className="shrink-0 text-xs font-semibold text-primary hover:underline">
          View log →
        </Link>
      </div>
      <ul className="mt-4 space-y-4">
        {items.map((item) => (
          <li key={item.id} className="flex gap-3">
            <span aria-hidden="true" className={`mt-1.5 size-2 shrink-0 rounded-full ${ACTIVITY_TONES[item.tone]}`} />
            <div className="min-w-0">
              <p className="text-[13px] font-bold text-ink">{item.title}</p>
              <p className="truncate text-xs text-ink-muted">{item.description}</p>
              <p className="text-[11px] text-placeholder">{item.time}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
