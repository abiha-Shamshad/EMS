import { useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoBadge } from '@/components/ui/DemoBadge';

/* ── Demo data ──────────────────────────────────────────────────────── */
const SYSTEM_SERVICES = [
  { name: 'API Gateway', host: 'api.ems-platform.com', uptime: '99.99%', latency: '82 ms', status: 'Operational' as const },
  { name: 'Primary Database', host: 'PostgreSQL cluster', uptime: '99.98%', latency: '24 ms', status: 'Operational' as const },
  { name: 'Background Workers', host: 'Queue processing service', uptime: '99.92%', latency: '146 ms', status: 'Degraded' as const },
  { name: 'File Storage', host: 'Secure document service', uptime: '99.97%', latency: '61 ms', status: 'Operational' as const },
];

const DEPLOYMENT_BARS = [
  { day: 'Mon', count: 5 },
  { day: 'Tue', count: 7 },
  { day: 'Wed', count: 4 },
  { day: 'Thu', count: 9 },
  { day: 'Fri', count: 6 },
  { day: 'Sat', count: 11 },
  { day: 'Sun', count: 6, highlight: true },
];
const MAX_BAR = Math.max(...DEPLOYMENT_BARS.map((b) => b.count));

const ROADMAP = [
  { name: 'API v2 rollout', category: 'Infrastructure', owner: 'Platform team', progress: 80, target: 'Oct 18', color: '#4f46d8' },
  { name: 'SSO & access controls', category: 'Security', owner: 'Security team', progress: 58, target: 'Oct 22', color: '#27c3a6' },
  { name: 'Analytics pipeline', category: 'Data platform', owner: 'Data team', progress: 34, target: 'Oct 29', color: '#a855f7' },
  { name: 'Worker queue optimization', category: 'Reliability', owner: 'Core services', progress: 70, target: 'Oct 16', color: '#f59e0b' },
];

const ALERTS = [
  { id: 'a1', title: 'Worker queue latency elevated', sub: 'Background workers · 12 min ago', badge: 'High priority', tone: 'warning' as const },
  { id: 'a2', title: 'API rate limit approaching', sub: 'API Gateway · 36 min ago', badge: 'Medium', tone: 'info' as const },
  { id: 'a3', title: 'Security scan completed', sub: 'Build pipeline · 1 hr ago', badge: 'Resolved', tone: 'success' as const },
];

const STAT_CARDS = [
  {
    id: 'uptime', label: 'System uptime', sub: 'Across core services',
    value: '99.98%', badge: '↑ 0.03%', tone: 'success',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    iconBg: 'bg-success-bg text-success-text',
    foot: 'Target ≥ 99.9%',
  },
  {
    id: 'incidents', label: 'Open incidents', sub: 'Requiring attention',
    value: '04', badge: '2 high priority', tone: 'warning',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
        <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
      </svg>
    ),
    iconBg: 'bg-warning-bg text-warning-text',
    foot: '1 new since yesterday',
  },
  {
    id: 'deployments', label: 'Deployments', sub: 'Successful this month',
    value: '186', badge: '+ 12.4%', tone: 'success',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <polyline points="16 16 12 12 8 16" /><line x1="12" y1="12" x2="12" y2="21" />
        <path d="M20.39 18.39A5 5 0 0 0 18 9h-1.26A8 8 0 1 0 3 16.3" />
      </svg>
    ),
    iconBg: 'bg-info-bg text-info-text',
    foot: 'Deployment success 98.4%',
  },
  {
    id: 'eng-projects', label: 'Engineering projects', sub: 'In active development',
    value: '12', badge: '3 near release', tone: 'info',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
      </svg>
    ),
    iconBg: 'bg-purple-bg text-purple-text',
    foot: '4 teams contributing',
  },
];

function StatusBadge({ status }: { status: 'Operational' | 'Degraded' }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
        status === 'Operational' ? 'bg-success-bg text-success-text' : 'bg-warning-bg text-warning-text'
      }`}
    >
      <span className={`size-1.5 rounded-full ${status === 'Operational' ? 'bg-success-text' : 'bg-warning-text'}`} />
      {status}
    </span>
  );
}

function AlertBadge({ tone, badge }: { tone: 'warning' | 'info' | 'success'; badge: string }) {
  const cls =
    tone === 'warning'
      ? 'bg-warning-bg text-warning-text'
      : tone === 'info'
        ? 'bg-info-bg text-info-text'
        : 'bg-success-bg text-success-text';
  return <span className={`rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${cls}`}>{badge}</span>;
}

function AlertIcon({ tone }: { tone: 'warning' | 'info' | 'success' }) {
  if (tone === 'warning')
    return (
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-warning-bg text-warning-text">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
          <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
      </span>
    );
  if (tone === 'success')
    return (
      <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-success-bg text-success-text">
        <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
          <polyline points="20 6 9 17 4 12" />
        </svg>
      </span>
    );
  return (
    <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-info-bg text-info-text">
      <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
    </span>
  );
}

const DATE_OPTIONS = ['Last 30 days', 'Last 7 days', 'Last 90 days'];

/** EMS_Screen_08_CTO_Dashboard */
export function CtoDashboardPage() {
  const [range, setRange] = useState(DATE_OPTIONS[0]);

  return (
    <div>
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            CTO Dashboard
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            Engineering performance, platform reliability, and delivery at a glance.
          </p>
        </div>
        <div className="flex items-center gap-2">
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
          <button
            type="button"
            className="h-10 rounded-xl bg-primary px-4 text-sm font-semibold text-white transition-colors hover:bg-primary-hover"
          >
            Generate Report
          </button>
        </div>
      </div>

      {/* R1 Source Disclaimer Banner */}
      <div className="mt-3 flex items-center justify-between rounded-xl border border-line-soft bg-panel-from px-4 py-2 text-xs text-ink-muted">
        <span>Engineering projects & roadmap are sourced live from EMS Work engine.</span>
        <span className="font-semibold text-accent">APM / external metrics: Telemetry connection pending in R1</span>
      </div>

      {/* Stat cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {STAT_CARDS.map((card) => (
          <div key={card.id} className="rounded-card bg-card p-5 shadow-card">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-[13px] font-semibold text-ink-muted">{card.label}</p>
                <p className="text-[11px] text-ink-muted">{card.sub}</p>
              </div>
              <span className={`flex size-10 items-center justify-center rounded-xl ${card.iconBg}`}>
                {card.icon}
              </span>
            </div>
            <p className="mt-3 text-[28px] font-extrabold tracking-tight text-ink">{card.value}</p>
            <p className="mt-1 flex items-center gap-1.5 text-[11px]">
              <span className={`rounded-full px-2 py-0.5 font-bold ${card.tone === 'success' ? 'bg-success-bg text-success-text' : card.tone === 'warning' ? 'bg-warning-bg text-warning-text' : 'bg-info-bg text-info-text'}`}>
                {card.badge}
              </span>
              <span className="text-ink-muted">{card.foot}</span>
            </p>
            <p className="mt-2 border-t border-line-soft pt-1.5 text-[10px] text-ink-muted">
              {card.id === 'eng-projects' ? '✓ Source: EMS Work Engine (live)' : 'ℹ Unavailable in R1 (needs APM)'}
            </p>
          </div>
        ))}
      </div>

      {/* System health + Deployment activity */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        {/* System health table */}
        <section aria-labelledby="sys-health-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
        <div className="flex items-center justify-between gap-3">
            <div>
              <h2 id="sys-health-heading" className="text-[15px] font-bold text-ink">System health</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Live status of essential platform services</p>
            </div>
            {SYSTEM_SERVICES.some(s => s.status === 'Degraded') ? (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-warning-bg px-3 py-1 text-[11px] font-semibold text-warning-text">
                <span className="size-1.5 rounded-full bg-warning-text" />
                {SYSTEM_SERVICES.filter(s => s.status === 'Degraded').length} service degraded
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 rounded-full bg-success-bg px-3 py-1 text-[11px] font-semibold text-success-text">
                <span className="size-1.5 rounded-full bg-success-text" />
                All systems operational
              </span>
            )}
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="border-b border-line-soft text-[11px] font-bold uppercase tracking-wide text-ink-muted">
                  <th className="pb-2 pr-4">Service</th>
                  <th className="pb-2 pr-4">Uptime</th>
                  <th className="pb-2 pr-4">Latency</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {SYSTEM_SERVICES.map((svc) => (
                  <tr key={svc.name}>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <span className={`flex size-7 items-center justify-center rounded-full ${svc.status === 'Operational' ? 'bg-success-bg text-success-text' : 'bg-warning-bg text-warning-text'}`}>
                          <svg viewBox="0 0 24 24" className="size-3.5" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
                            {svc.status === 'Operational' ? <polyline points="20 6 9 17 4 12" /> : <line x1="12" y1="5" x2="12" y2="19" />}
                          </svg>
                        </span>
                        <div>
                          <p className="text-[13px] font-semibold text-ink">{svc.name}</p>
                          <p className="text-[11px] text-ink-muted">{svc.host}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-[13px] font-semibold text-ink">{svc.uptime}</td>
                    <td className="py-3 pr-4 text-[13px] text-ink-muted">{svc.latency}</td>
                    <td className="py-3"><StatusBadge status={svc.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Deployment activity */}
        <section aria-labelledby="deploy-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h2 id="deploy-heading" className="text-[15px] font-bold text-ink">Deployment activity</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Successful releases over the last 7 days</p>
            </div>
            <span className="text-xs font-semibold text-ink-muted">Weekly view</span>
          </div>
          <p className="mt-3 text-[26px] font-extrabold text-ink">48 deployments</p>
          <p className="text-[12px] font-bold text-success-text">+8.2%</p>
          <div className="mt-4 flex h-24 items-end gap-2" aria-label="Deployment chart">
            {DEPLOYMENT_BARS.map((bar) => (
              <div key={bar.day} className="flex flex-1 flex-col items-center gap-1">
                <div
                  className={`w-full rounded-t-md ${bar.highlight ? 'bg-primary' : 'bg-accent-soft'}`}
                  style={{ height: `${(bar.count / MAX_BAR) * 88}px` }}
                />
                <span className="text-[10px] text-ink-muted">{bar.day}</span>
              </div>
            ))}
          </div>
          <div className="mt-4 border-t border-line-soft pt-3">
            <p className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-ink-muted">
                <span className="size-1.5 rounded-full bg-success-text" />
                Success rate
              </span>
              <span className="font-bold text-ink">98.4%</span>
            </p>
            <p className="mt-1 text-[10px] text-ink-muted">Illustrative sample metrics</p>
          </div>
        </section>
      </div>

      {/* Engineering roadmap + Technical alerts */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        {/* Roadmap */}
        <section aria-labelledby="roadmap-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-start justify-between gap-2">
            <div>
              <h2 id="roadmap-heading" className="text-[15px] font-bold text-ink">Engineering roadmap</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Current delivery status by initiative</p>
            </div>
          </div>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-sm">
              <thead>
                <tr className="border-b border-line-soft text-[10px] font-bold uppercase tracking-wide text-ink-muted">
                  <th className="pb-2 pr-4">Initiative</th>
                  <th className="pb-2 pr-4">Owner</th>
                  <th className="pb-2 pr-4 w-36">Progress</th>
                  <th className="pb-2">Target</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {ROADMAP.map((item) => (
                  <tr key={item.name}>
                    <td className="py-3 pr-4">
                      <p className="text-[13px] font-semibold text-ink">{item.name}</p>
                      <p className="text-[11px] text-ink-muted">{item.category}</p>
                    </td>
                    <td className="py-3 pr-4 text-[13px] text-ink-muted">{item.owner}</td>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="h-2 flex-1 overflow-hidden rounded-full bg-search-bg">
                          <div className="h-full rounded-full" style={{ width: `${item.progress}%`, backgroundColor: item.color }} />
                        </div>
                        <span className="text-[11px] font-semibold text-ink">{item.progress}%</span>
                      </div>
                    </td>
                    <td className="py-3 text-[13px] font-medium text-ink-muted">{item.target}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link to="/app/projects" className="mt-4 inline-block text-[13px] font-semibold text-primary hover:underline">
            View engineering roadmap →
          </Link>
        </section>

        {/* Technical alerts */}
        <section aria-labelledby="alerts-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-start justify-between gap-2">
            <h2 id="alerts-heading" className="text-[15px] font-bold text-ink">Technical alerts</h2>
            <span className="rounded-full bg-warning-bg px-2.5 py-0.5 text-[11px] font-bold text-warning-text">4 open</span>
          </div>
          <p className="mt-0.5 text-xs text-ink-muted">Items that may need your attention</p>
          <ul className="mt-4 space-y-3">
            {ALERTS.map((alert) => (
              <li key={alert.id} className="flex items-start gap-3 rounded-xl border border-line-soft p-3">
                <AlertIcon tone={alert.tone} />
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-semibold text-ink">{alert.title}</p>
                  <p className="text-[11px] text-ink-muted">{alert.sub}</p>
                </div>
                <AlertBadge tone={alert.tone} badge={alert.badge} />
              </li>
            ))}
          </ul>
          <Link to="/app/incidents" className="mt-4 inline-block text-[13px] font-semibold text-primary hover:underline">
            View all incidents →
          </Link>
        </section>
      </div>
    </div>
  );
}
