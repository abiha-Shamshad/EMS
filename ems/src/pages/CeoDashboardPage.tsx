import { useState } from 'react';
import { ActivityFeed, AttentionList } from '@/components/dashboard/DashboardPanels';
import { RevenueChart } from '@/components/dashboard/RevenueChart';
import { StatCard } from '@/components/dashboard/StatCard';
import { WorkforceDonut } from '@/components/dashboard/WorkforceDonut';
import { ChevronDownIcon } from '@/components/layout/icons';
import { DemoBadge } from '@/components/ui/DemoBadge';
import { DEMO_ACTIVITY, DEMO_ATTENTION, DEMO_REVENUE, DEMO_STATS, DEMO_WORKFORCE } from '@/demo/fixtures';
import { getSession } from '@/lib/session';

const DATE_OPTIONS = ['Oct 10, 2026 · Today', 'Oct 09, 2026 · Yesterday', 'Last 7 days', 'Last 30 days'];

/** EMS_Screen_07_CEO_Dashboard. Greeting + stat cards + revenue/workforce + panels. */
export function CeoDashboardPage() {
  const session = getSession();
  const firstName = (session?.user.name ?? '').split(' ')[0] || 'there';
  const [range, setRange] = useState(DATE_OPTIONS[0]);
  const totalWorkforce = DEMO_WORKFORCE.reduce((sum, slice) => sum + slice.count, 0);

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            Good morning, {firstName}!
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">Here&apos;s what&apos;s happening across your company today.</p>
        </div>
        <label className="relative inline-flex w-full sm:w-auto">
          <span className="sr-only">Date range</span>
          <select
            value={range}
            onChange={(event) => setRange(event.target.value)}
            className="h-10 w-full appearance-none rounded-xl border border-line-soft bg-white pr-9 pl-3.5 text-xs font-medium text-ink shadow-card focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none sm:w-auto"
          >
            {DATE_OPTIONS.map((option) => (
              <option key={option} value={option}>{option}</option>
            ))}
          </select>
          <ChevronDownIcon className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-muted" />
        </label>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {DEMO_STATS.map((datum) => (
          <StatCard key={datum.id} datum={datum} />
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <section aria-labelledby="revenue-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="revenue-heading" className="text-[15px] font-bold text-ink">Revenue overview</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Monthly revenue performance</p>
            </div>
            <span className="shrink-0 rounded-full bg-search-bg px-2.5 py-1 text-[11px] font-semibold text-ink-muted">
              Last 6 months
            </span>
          </div>
          <div className="mt-3">
            <RevenueChart points={DEMO_REVENUE} />
          </div>
        </section>

        <section aria-labelledby="workforce-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <h2 id="workforce-heading" className="text-[15px] font-bold text-ink">Workforce overview</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Employees by department</p>
          <div className="mt-4">
            <WorkforceDonut slices={DEMO_WORKFORCE} total={totalWorkforce} />
          </div>
          <div className="mt-4 border-t border-line-soft pt-3">
            <p className="flex items-center justify-between text-xs">
              <span className="text-ink-muted">Headcount growth</span>
              <span className="font-bold text-success-text">+8.2% this month</span>
            </p>
            <div aria-hidden="true" className="mt-2 h-1.5 overflow-hidden rounded-full bg-search-bg">
              <div className="h-full w-[72%] rounded-full bg-chart-line" />
            </div>
          </div>
        </section>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        <AttentionList items={DEMO_ATTENTION} />
        <ActivityFeed items={DEMO_ACTIVITY} />
      </div>
    </div>
  );
}
