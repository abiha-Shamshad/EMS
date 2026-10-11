import { useState } from 'react';
import { Link } from 'react-router-dom';
import { DemoBadge } from '@/components/ui/DemoBadge';

/* ── Demo data ──────────────────────────────────────────────────────── */
const TRANSACTIONS = [
  { id: 't1', description: 'Client subscription payment', ref: 'INV-2026-1048', category: 'Revenue', date: 'Oct 10', amount: '+$8,400', positive: true },
  { id: 't2', description: 'Cloud hosting services', ref: 'BILL-2026-882', category: 'Infrastructure', date: 'Oct 09', amount: '-$1,280', positive: false },
  { id: 't3', description: 'Software licenses', ref: 'BILL-2026-879', category: 'Software', date: 'Oct 08', amount: '-$640', positive: false },
  { id: 't4', description: 'Professional services', ref: 'INV-2026-1039', category: 'Revenue', date: 'Oct 07', amount: '+$3,200', positive: true },
];

const BUDGET_ITEMS = [
  { label: 'Overall budget', used: 72, total: null, color: '#4f46d8' },
  { label: 'Engineering', used: 78, display: '$31.2K / $40K', color: '#4f46d8' },
  { label: 'People & operations', used: 61, display: '$18.4K / $30K', color: '#27c3a6' },
  { label: 'Marketing & sales', used: 64, display: '$12.8K / $20K', color: '#22c55e' },
];

const FINANCIAL_ATTENTION = [
  { id: 'f1', title: 'Overdue customer invoices', sub: '7 invoices · $12,450 outstanding', badge: 'Follow up', tone: 'warning' as const },
  { id: 'f2', title: 'Engineering budget nearing limit', sub: '78% of monthly allocation used', badge: 'Review', tone: 'info' as const },
  { id: 'f3', title: 'Payroll forecast updated', sub: 'Next cycle · Oct 15', badge: 'On track', tone: 'success' as const },
];

// Revenue chart points (6 months)
const REVENUE_POINTS = [78, 112, 98, 152, 178, 208];
const EXPENSE_POINTS = [55, 72, 68, 85, 95, 110];
const MONTHS = ['May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct'];
const MAX_VAL = Math.max(...REVENUE_POINTS, ...EXPENSE_POINTS);

function polylinePoints(data: number[], width: number, height: number) {
  const step = width / (data.length - 1);
  return data
    .map((v, i) => `${i * step},${height - (v / MAX_VAL) * height}`)
    .join(' ');
}

function RevenueExpensesChart() {
  const W = 540;
  const H = 140;
  const rPts = polylinePoints(REVENUE_POINTS, W, H);
  const ePts = polylinePoints(EXPENSE_POINTS, W, H);

  // area fill polygon
  const rArea = `0,${H} ${rPts} ${W},${H}`;
  const eArea = `0,${H} ${ePts} ${W},${H}`;

  return (
    <div className="relative mt-4 w-full overflow-x-auto">
      <svg viewBox={`0 0 ${W} ${H + 24}`} className="w-full" aria-label="Revenue and expenses chart">
        {/* grid lines */}
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <line key={f} x1={0} y1={H - f * H} x2={W} y2={H - f * H} stroke="#e8ecf6" strokeWidth={1} />
        ))}
        {/* Y-labels */}
        {[50, 100, 150, 200].map((v) => (
          <text key={v} x={-4} y={H - (v / MAX_VAL) * H + 4} textAnchor="end" fontSize={9} fill="#97a3c2">
            ${v}k
          </text>
        ))}
        {/* Expense area */}
        <polygon points={eArea} fill="#e3e9ff" fillOpacity={0.4} />
        <polyline points={ePts} fill="none" stroke="#a5b4fc" strokeWidth={2} />
        {/* Revenue area */}
        <polygon points={rArea} fill="#4f46d8" fillOpacity={0.08} />
        <polyline points={rPts} fill="none" stroke="#4f46d8" strokeWidth={2.5} />
        {/* Revenue dots */}
        {REVENUE_POINTS.map((v, i) => (
          <circle key={i} cx={(i / (REVENUE_POINTS.length - 1)) * W} cy={H - (v / MAX_VAL) * H} r={4} fill="#4f46d8" />
        ))}
        {/* X labels */}
        {MONTHS.map((m, i) => (
          <text key={m} x={(i / (MONTHS.length - 1)) * W} y={H + 16} textAnchor="middle" fontSize={10} fill="#97a3c2">
            {m}
          </text>
        ))}
      </svg>
    </div>
  );
}

const STAT_CARDS = [
  {
    id: 'revenue', label: 'Total revenue', sub: 'Current month',
    value: '$184.6K', badge: '↑ 8.6% MoM', tone: 'success',
    foot: 'Compared with September',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
    iconBg: 'bg-success-bg text-success-text',
  },
  {
    id: 'expenses', label: 'Operating expenses', sub: 'Current month',
    value: '$62.4K', badge: '↑ 3.2%', tone: 'success',
    foot: 'Within planned limits',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <rect x="2" y="5" width="20" height="14" rx="2" /><line x1="2" y1="10" x2="22" y2="10" />
      </svg>
    ),
    iconBg: 'bg-warning-bg text-warning-text',
  },
  {
    id: 'profit', label: 'Net profit', sub: 'After operating costs',
    value: '$122.2K', badge: '↑ 14.1% MoM', tone: 'success',
    foot: 'Margin 66.2%',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <line x1="12" y1="20" x2="12" y2="10" /><line x1="18" y1="20" x2="18" y2="4" /><line x1="6" y1="20" x2="6" y2="16" />
      </svg>
    ),
    iconBg: 'bg-info-bg text-info-text',
  },
  {
    id: 'invoices', label: 'Outstanding invoices', sub: 'Awaiting payment',
    value: '$28.7K', badge: '7 overdue invoices', tone: 'warning',
    foot: 'Follow-up recommended',
    icon: (
      <svg viewBox="0 0 24 24" className="size-5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" /><line x1="16" y1="17" x2="8" y2="17" /><polyline points="10 9 9 9 8 9" />
      </svg>
    ),
    iconBg: 'bg-purple-bg text-purple-text',
  },
];

const DATE_OPTIONS = ['October 2026', 'September 2026', 'Last 6 months'];

/** EMS_Screen_09_CFO_Dashboard */
export function CfoDashboardPage() {
  const [range, setRange] = useState(DATE_OPTIONS[0]);

  return (
    <div>
      {/* Page header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            CFO Dashboard
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            Track financial performance, cash flow, budgets, and upcoming obligations.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <label className="relative inline-flex w-full sm:w-auto">
            <span className="sr-only">Date period</span>
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
            Export Report
          </button>
        </div>
      </div>

      {/* R1 Source Disclaimer Banner */}
      <div className="mt-3 flex items-center justify-between rounded-xl border border-line-soft bg-panel-from px-4 py-2 text-xs text-ink-muted">
        <span>Invoices, payments & financial leakage findings are live from EMS Finance engine.</span>
        <span className="font-semibold text-accent">External expenses & payroll: Accounting sync scheduled for Release 2</span>
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
            <p className="mt-3 text-[26px] font-extrabold tracking-tight text-ink">{card.value}</p>
            <p className="mt-1 flex items-center gap-1.5 text-[11px]">
              <span className={`rounded-full px-2 py-0.5 font-bold ${card.tone === 'success' ? 'bg-success-bg text-success-text' : card.tone === 'warning' ? 'bg-warning-bg text-warning-text' : 'bg-info-bg text-info-text'}`}>
                {card.badge}
              </span>
              <span className="text-ink-muted">{card.foot}</span>
            </p>
            <p className="mt-2 border-t border-line-soft pt-1.5 text-[10px] text-ink-muted">
              {card.id === 'mrr' || card.id === 'invoiced'
                ? '✓ Source: EMS Finance Engine (live)'
                : 'ℹ External Source (accounting adapter pending in R1)'}
            </p>
          </div>
        ))}
      </div>

      {/* Revenue & expenses chart + Budget utilization */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        {/* Revenue & expenses */}
        <section aria-labelledby="rev-exp-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 id="rev-exp-heading" className="text-[15px] font-bold text-ink">Revenue &amp; expenses</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Monthly comparison · last 6 months</p>
            </div>
            <div className="flex items-center gap-3 text-[11px] font-semibold">
              <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-primary" />Revenue</span>
              <span className="flex items-center gap-1.5"><span className="size-2.5 rounded-full bg-accent-soft" />Expenses</span>
            </div>
          </div>
          <RevenueExpensesChart />
          <p className="mt-3 text-[12px] font-semibold text-ink-muted">
            October revenue is trending above the previous month.
          </p>
        </section>

        {/* Budget utilization */}
        <section aria-labelledby="budget-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <h2 id="budget-heading" className="text-[15px] font-bold text-ink">Budget utilization</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Spend against monthly allocations</p>
          <ul className="mt-5 space-y-4">
            {BUDGET_ITEMS.map((item) => (
              <li key={item.label}>
                <div className="flex items-center justify-between text-[13px]">
                  <span className="font-semibold text-ink">{item.label}</span>
                  {item.display ? (
                    <span className="text-ink-muted">{item.display}</span>
                  ) : (
                    <span className="font-bold text-ink">{item.used}% used</span>
                  )}
                </div>
                <div className="mt-1.5 h-2 overflow-hidden rounded-full bg-search-bg">
                  <div className="h-full rounded-full" style={{ width: `${item.used}%`, backgroundColor: item.color }} />
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-5 text-[10px] text-ink-muted">Illustrative sample financial data</p>
        </section>
      </div>

      {/* Recent transactions + Financial attention */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_340px]">
        {/* Recent transactions */}
        <section aria-labelledby="transactions-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <h2 id="transactions-heading" className="text-[15px] font-bold text-ink">Recent transactions</h2>
          <p className="mt-0.5 text-xs text-ink-muted">Latest recorded income and outgoing payments</p>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[480px] text-left text-sm">
              <thead>
                <tr className="border-b border-line-soft text-[10px] font-bold uppercase tracking-wide text-ink-muted">
                  <th className="pb-2 pr-4">Description</th>
                  <th className="pb-2 pr-4">Category</th>
                  <th className="pb-2 pr-4">Date</th>
                  <th className="pb-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line-soft">
                {TRANSACTIONS.map((tx) => (
                  <tr key={tx.id}>
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2.5">
                        <span className={`flex size-8 shrink-0 items-center justify-center rounded-full text-sm font-bold ${tx.positive ? 'bg-success-bg text-success-text' : 'bg-warning-bg text-warning-text'}`}>
                          {tx.positive ? '+' : '−'}
                        </span>
                        <div>
                          <p className="text-[13px] font-semibold text-ink">{tx.description}</p>
                          <p className="text-[11px] text-ink-muted">{tx.ref}</p>
                        </div>
                      </div>
                    </td>
                    <td className="py-3 pr-4 text-[13px] text-ink-muted">{tx.category}</td>
                    <td className="py-3 pr-4 text-[13px] text-ink-muted">{tx.date}</td>
                    <td className={`py-3 text-right text-[13px] font-bold ${tx.positive ? 'text-success-text' : 'text-danger'}`}>
                      {tx.amount}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Link to="/app/revenue-expenses" className="mt-4 inline-block text-[13px] font-semibold text-primary hover:underline">
            View all transactions →
          </Link>
        </section>

        {/* Financial attention */}
        <section
          aria-labelledby="fin-attention-heading"
          className="rounded-card border-2 border-primary/30 bg-card p-5 shadow-card sm:p-6"
        >
          <div className="flex items-start justify-between gap-2">
            <h2 id="fin-attention-heading" className="text-[15px] font-bold text-ink">Financial attention</h2>
            <span className="rounded-full bg-warning-bg px-2.5 py-0.5 text-[11px] font-bold text-warning-text">3 items</span>
          </div>
          <p className="mt-0.5 text-xs text-ink-muted">Items to review this period</p>
          <ul className="mt-4 space-y-3">
            {FINANCIAL_ATTENTION.map((item) => (
              <li key={item.id} className="flex items-start gap-3 rounded-xl border border-line-soft p-3">
                <span className={`flex size-8 shrink-0 items-center justify-center rounded-full ${item.tone === 'warning' ? 'bg-warning-bg text-warning-text' : item.tone === 'success' ? 'bg-success-bg text-success-text' : 'bg-info-bg text-info-text'}`}>
                  <svg viewBox="0 0 24 24" className="size-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                    {item.tone === 'warning' && (
                      <><path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" /></>
                    )}
                    {item.tone === 'info' && (
                      <><circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" /></>
                    )}
                    {item.tone === 'success' && <polyline points="20 6 9 17 4 12" />}
                  </svg>
                </span>
                <div className="min-w-0 flex-1">
                  <p className="text-[13px] font-semibold text-ink">{item.title}</p>
                  <p className="text-[11px] text-ink-muted">{item.sub}</p>
                </div>
                <span className={`shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${item.tone === 'warning' ? 'bg-warning-bg text-warning-text' : item.tone === 'success' ? 'bg-success-bg text-success-text' : 'bg-info-bg text-info-text'}`}>
                  {item.badge}
                </span>
              </li>
            ))}
          </ul>
          <Link to="/app/invoices" className="mt-4 inline-block text-[13px] font-semibold text-primary hover:underline">
            Open finance tasks →
          </Link>
        </section>
      </div>
    </div>
  );
}
