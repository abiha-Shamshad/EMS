import { useState } from 'react';
import { DemoBadge } from '@/components/ui/DemoBadge';
import { Badge } from '@/components/ui/Badge';
import { DEMO_DIRECTORY, DEMO_PROJECTS } from '@/demo/fixtures';
import { getSession } from '@/lib/session';

const DATE_OPTIONS = ['Oct 10, 2026 · Today', 'Yesterday', 'Last 7 days', 'Last 30 days'];

const COO_KPI_CARDS = [
  {
    id: 'coo-workforce',
    label: 'Live presence',
    sub: 'Checked-in staff',
    value: '38 / 42',
    badge: '90.5% active',
    tone: 'success' as const,
    foot: '4 on scheduled breaks',
  },
  {
    id: 'coo-projects',
    label: 'Active projects',
    sub: 'Under delivery',
    value: '08',
    badge: '6 on track',
    tone: 'info' as const,
    foot: '2 in client review',
  },
  {
    id: 'coo-crm',
    label: 'Pipeline conversions',
    sub: 'Win to kickoff rate',
    value: '84.2%',
    badge: '+ 5.4%',
    tone: 'success' as const,
    foot: 'Avg 2.1 days to kickoff',
  },
  {
    id: 'coo-ops',
    label: 'Automations run',
    sub: 'Rules engine throughput',
    value: '1,420',
    badge: '100% success',
    tone: 'purple' as const,
    foot: '0 loop skips detected',
  },
];

const OPS_INCIDENTS = [
  { id: 'op1', title: 'Northwind Project kickoff completed', sub: 'Client activated · 12 tasks seeded', time: '18 min ago', tone: 'success' as const },
  { id: 'op2', title: 'Break limit reached: Tariq Mehmood', sub: 'Exceeded 45m daily allowance · Manager review', time: '34 min ago', tone: 'warning' as const },
  { id: 'op3', title: 'Stale deal nudge triggered: Contoso', sub: 'No activity 14 days · Reassigned to Usman', time: '1 hr ago', tone: 'info' as const },
];

export function CooDashboardPage() {
  const session = getSession();
  const userName = session?.user.name ?? 'Nadia Khan';
  const firstName = userName.split(' ')[0] || 'Nadia';
  const [range, setRange] = useState(DATE_OPTIONS[0]);

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            COO Operations Dashboard
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            Workforce presence, project delivery flow, and cross-functional operations. Welcome back, {firstName}!
          </p>
        </div>
        <label className="relative inline-flex w-full sm:w-auto">
          <span className="sr-only">Date range</span>
          <select
            value={range}
            onChange={(e) => setRange(e.target.value)}
            className="h-10 w-full appearance-none rounded-xl border border-line-soft bg-white pr-9 pl-3.5 text-xs font-medium text-ink shadow-card focus:border-accent focus:outline-none sm:w-auto"
          >
            {DATE_OPTIONS.map((o) => (
              <option key={o} value={o}>{o}</option>
            ))}
          </select>
          <svg viewBox="0 0 20 20" className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-ink-muted" fill="none" stroke="currentColor" strokeWidth={2}>
            <path d="m5 7 5 5 5-5" />
          </svg>
        </label>
      </div>

      {/* KPI Cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {COO_KPI_CARDS.map((card) => (
          <div key={card.id} className="rounded-card bg-card p-5 shadow-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[13px] font-semibold text-ink-muted">{card.label}</p>
                <p className="text-[11px] text-ink-muted">{card.sub}</p>
              </div>
              <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-bold ${
                card.tone === 'success' ? 'bg-success-bg text-success-text' :
                card.tone === 'purple' ? 'bg-purple-bg text-purple-text' : 'bg-info-bg text-info-text'
              }`}>
                {card.badge}
              </span>
            </div>
            <p className="mt-3 text-[28px] font-extrabold tracking-tight text-ink">{card.value}</p>
            <p className="mt-1 text-xs text-ink-muted">{card.foot}</p>
          </div>
        ))}
      </div>

      {/* Operations Overview Grid */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        {/* Live Workforce Presence */}
        <section aria-labelledby="live-presence-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 id="live-presence-heading" className="text-[15px] font-bold text-ink">Live Employee Room Presence</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Consented real-time work session tracking</p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-full bg-success-bg px-2.5 py-1 text-[11px] font-semibold text-success-text">
              <span className="size-1.5 rounded-full bg-success-text" />
              Audited live view ready
            </span>
          </div>

          <div className="mt-4 overflow-x-auto rounded-xl border border-line-soft">
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead>
                <tr className="bg-panel-from text-xs text-ink-muted uppercase">
                  <th scope="col" className="px-4 py-3 font-semibold">Employee</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Department</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Current Task</th>
                  <th scope="col" className="px-4 py-3 font-semibold">Status</th>
                  <th scope="col" className="px-4 py-3 font-semibold text-right">Online</th>
                </tr>
              </thead>
              <tbody>
                {DEMO_DIRECTORY.map((member) => (
                  <tr key={member.id} className="border-t border-line-soft">
                    <td className="px-4 py-3">
                      <div>
                        <span className="block font-bold text-ink">{member.name}</span>
                        <span className="block text-xs text-ink-muted">{member.role}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-ink-body">{member.department}</td>
                    <td className="px-4 py-3 font-medium text-ink">
                      {member.status === 'Active' ? 'Sprint Delivery & Tasks' : 'Away / On Break'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge tone={member.status === 'Active' ? 'success' : member.status === 'On leave' ? 'warning' : 'info'}>
                        {member.status}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right font-medium text-ink-muted">
                      {member.status === 'Active' ? '5h 12m' : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Operational Attention & Activity */}
        <div className="space-y-4">
          <section aria-labelledby="ops-events-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
            <h2 id="ops-events-heading" className="text-[15px] font-bold text-ink">Operational Events</h2>
            <p className="mt-0.5 text-xs text-ink-muted">Rules engine & workflow activity</p>
            <ul className="mt-4 space-y-3">
              {OPS_INCIDENTS.map((item) => (
                <li key={item.id} className="rounded-xl border border-line-soft p-3">
                  <div className="flex items-start justify-between gap-2">
                    <p className="text-[13px] font-bold text-ink">{item.title}</p>
                    <span className="text-[11px] text-ink-muted">{item.time}</span>
                  </div>
                  <p className="mt-1 text-xs text-ink-muted">{item.sub}</p>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="project-health-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
            <h2 id="project-health-heading" className="text-[15px] font-bold text-ink">Active Project Delivery</h2>
            <p className="mt-0.5 text-xs text-ink-muted">Delivery milestones across teams</p>
            <div className="mt-4 space-y-3">
              {DEMO_PROJECTS.slice(0, 3).map((p) => (
                <div key={p.id} className="rounded-xl border border-line-soft p-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[13px] font-bold text-ink">{p.name}</span>
                    <Badge tone={p.status === 'On track' ? 'success' : 'warning'}>{p.status}</Badge>
                  </div>
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-search-bg">
                    <div className="h-full rounded-full bg-chart-line" style={{ width: `${p.progress}%` }} />
                  </div>
                  <p className="mt-1 text-[11px] text-ink-muted">{p.progress}% completed · Client: {p.client}</p>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
