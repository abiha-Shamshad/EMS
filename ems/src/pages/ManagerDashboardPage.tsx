import { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { DemoBadge } from '@/components/ui/DemoBadge';
import { useToast } from '@/components/ui/Toast';
import { getSession } from '@/lib/session';

interface TeamTask {
  id: string;
  title: string;
  assignee: string;
  project: string;
  status: 'todo' | 'active' | 'review' | 'done';
}

const INITIAL_TEAM_TASKS: TeamTask[] = [
  { id: 'tt-1', title: 'Implement Auth Session tokens', assignee: 'Bilal Ahmed', project: 'Core Platform', status: 'active' },
  { id: 'tt-2', title: 'Design Room Presence widget', assignee: 'Zainab Abbas', project: 'Design System', status: 'review' },
  { id: 'tt-3', title: 'Configure PostgreSQL RLS policies', assignee: 'Hamza Farooq', project: 'Database API', status: 'done' },
  { id: 'tt-4', title: 'Review robotparser crawl constraints', assignee: 'Bilal Ahmed', project: 'Lead Hunter', status: 'todo' },
];

const MY_DEALS = [
  { id: 'd-1', title: 'Acme Enterprise Migration', client: 'Acme Corp', value: '$24,000', stage: 'Negotiation', probability: '70%' },
  { id: 'd-2', title: 'Nexus Mobile App V2', client: 'Nexus Tech', value: '$18,500', stage: 'Proposal', probability: '50%' },
  { id: 'd-3', title: 'Vertex Design System', client: 'Vertex Global', value: '$12,000', stage: 'Qualified', probability: '25%' },
];

export function ManagerDashboardPage() {
  const session = getSession();
  const toast = useToast();
  const userName = session?.user.name ?? 'Ava Chen';
  const firstName = userName.split(' ')[0] || 'Ava';

  const [tasks, setTasks] = useState(INITIAL_TEAM_TASKS);
  const [teamLeave, setTeamLeave] = useState([
    { id: 'tl-1', name: 'Bilal Ahmed', type: 'Casual Leave', dates: 'Tomorrow (Oct 12)', reason: 'Personal matters', status: 'pending' },
    { id: 'tl-2', name: 'Hamza Farooq', type: 'Extended Break', dates: 'Today · 30m', reason: 'Team lunch', status: 'pending' },
  ]);

  function handleTaskStatus(id: string, newStatus: TeamTask['status']) {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, status: newStatus } : t))
    );
    toast.notify(`Task status updated to ${newStatus}.`);
  }

  function handleLeave(id: string, action: 'approved' | 'rejected') {
    setTeamLeave((prev) =>
      prev.map((l) => (l.id === id ? { ...l, status: action } : l))
    );
    toast.notify(`Request has been ${action}.`);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            Manager Team Dashboard
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            Team task assignments, sprint delivery, leave approvals, and assigned pipeline deals. Welcome back, {firstName}!
          </p>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Team Members</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">06</p>
          <p className="mt-1 text-xs font-semibold text-success-text">All checked in & active</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Active Sprint Tasks</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            {tasks.filter((t) => t.status === 'active' || t.status === 'review').length}
          </p>
          <p className="mt-1 text-xs text-ink-muted">1 in review · 1 in progress</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Pending Team Requests</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            {teamLeave.filter((l) => l.status === 'pending').length}
          </p>
          <p className="mt-1 text-xs font-semibold text-warning-text">Awaiting your approval</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">My Deal Pipeline</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">$54.5k</p>
          <p className="mt-1 text-xs text-ink-muted">3 active opportunities</p>
        </div>
      </div>

      {/* Main Grid: Team Tasks & Pending Requests */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        {/* Left Column: Team Tasks & Kanban Board */}
        <section aria-labelledby="team-tasks-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 id="team-tasks-heading" className="text-[15px] font-bold text-ink">Assigned Team Tasks</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Track progress and update task stages</p>
            </div>
            <span className="text-xs font-semibold text-ink-muted">{tasks.length} tasks</span>
          </div>

          <div className="mt-4 space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="rounded-xl border border-line-soft p-4">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-bold text-ink">{task.title}</p>
                    <p className="mt-0.5 text-xs text-ink-muted">
                      Assignee: <span className="font-semibold text-ink">{task.assignee}</span> · Project: {task.project}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge
                      tone={
                        task.status === 'done' ? 'success' :
                        task.status === 'active' ? 'info' :
                        task.status === 'review' ? 'purple' : 'neutral'
                      }
                    >
                      {task.status.toUpperCase()}
                    </Badge>
                    {task.status !== 'done' && (
                      <button
                        type="button"
                        onClick={() =>
                          handleTaskStatus(
                            task.id,
                            task.status === 'todo' ? 'active' : task.status === 'active' ? 'review' : 'done'
                          )
                        }
                        className="rounded-lg bg-panel-from px-2.5 py-1 text-xs font-semibold text-primary hover:bg-nav-active"
                      >
                        Advance &rarr;
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right Column: Team Approvals & My Deals */}
        <div className="space-y-4">
          <section aria-labelledby="team-approvals-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
            <h2 id="team-approvals-heading" className="text-[15px] font-bold text-ink">Team Leave & Break Requests</h2>
            <p className="mt-0.5 text-xs text-ink-muted">Requests from your direct reports</p>
            <div className="mt-4 space-y-3">
              {teamLeave.map((item) => (
                <div key={item.id} className="rounded-xl border border-line-soft p-3">
                  <div className="flex items-start justify-between">
                    <div>
                      <p className="font-bold text-ink">{item.name}</p>
                      <p className="text-xs text-ink-muted">{item.type} · {item.dates}</p>
                      <p className="mt-1 text-xs italic text-ink-muted">&ldquo;{item.reason}&rdquo;</p>
                    </div>
                  </div>
                  <div className="mt-3 flex items-center justify-end gap-2 border-t border-line-soft pt-2">
                    {item.status === 'pending' ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleLeave(item.id, 'approved')}
                          className="rounded-lg bg-success-bg px-2.5 py-1 text-xs font-bold text-success-text hover:bg-success hover:text-white"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => handleLeave(item.id, 'rejected')}
                          className="rounded-lg bg-danger-soft px-2.5 py-1 text-xs font-bold text-danger hover:bg-danger hover:text-white"
                        >
                          Decline
                        </button>
                      </>
                    ) : (
                      <Badge tone={item.status === 'approved' ? 'success' : 'danger'}>
                        {item.status === 'approved' ? 'Approved' : 'Declined'}
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section aria-labelledby="my-deals-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
            <h2 id="my-deals-heading" className="text-[15px] font-bold text-ink">My CRM Deals</h2>
            <p className="mt-0.5 text-xs text-ink-muted">Assigned pipeline opportunities</p>
            <div className="mt-4 space-y-3">
              {MY_DEALS.map((deal) => (
                <div key={deal.id} className="rounded-xl border border-line-soft p-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-ink">{deal.title}</span>
                    <span className="font-extrabold text-primary">{deal.value}</span>
                  </div>
                  <div className="mt-1.5 flex items-center justify-between text-xs text-ink-muted">
                    <span>{deal.client}</span>
                    <Badge tone="info">{deal.stage} ({deal.probability})</Badge>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
