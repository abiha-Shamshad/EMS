import { useState } from 'react';
import { AddEmployeeModal, type NewEmployeeData } from '@/components/hr/AddEmployeeModal';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DemoBadge } from '@/components/ui/DemoBadge';
import { useToast } from '@/components/ui/Toast';
import { DEMO_DIRECTORY } from '@/demo/fixtures';
import { getSession } from '@/lib/session';

interface LeaveRequestItem {
  id: string;
  name: string;
  role: string;
  type: string;
  days: string;
  dates: string;
  reason: string;
  status: 'pending' | 'approved' | 'rejected';
}

const INITIAL_LEAVE_REQUESTS: LeaveRequestItem[] = [
  { id: 'lr-1', name: 'Zainab Abbas', role: 'UI/UX Designer', type: 'Annual Leave', days: '3 days', dates: 'Oct 14 - Oct 16', reason: 'Family travel', status: 'pending' },
  { id: 'lr-2', name: 'Hamza Farooq', role: 'Frontend Engineer', type: 'Sick Leave', days: '1 day', dates: 'Oct 12', reason: 'Medical appointment', status: 'pending' },
  { id: 'lr-3', name: 'Mariam Tariq', role: 'QA Analyst', type: 'Casual Leave', days: '2 days', dates: 'Oct 19 - Oct 20', reason: 'Personal errands', status: 'pending' },
];

const HR_AGENT_KNOWLEDGE: Record<string, { answer: string; source: string }> = {
  'late_arrival': {
    answer: 'Per Company Policy, shift starts at 09:00 with a 10-minute grace period. Check-in after 09:10 is recorded as late. 3 late arrivals within 7 days automatically triggers an HR notification under rule late_three_times.',
    source: 'Policy POL-ATT-01 · Section 5.2 Work Hours',
  },
  'leave_balance': {
    answer: 'Full-time employees receive 18 days annual leave and 8 days casual leave per calendar year. Unused annual leave up to 5 days can carry forward.',
    source: 'Policy POL-LEV-04 · Annual Entitlements',
  },
  'who_on_leave': {
    answer: 'Currently 2 employees are on approved leave today: Bilal Ahmed (Casual Leave, returns Oct 13) and Sana Mir (Annual Leave, returns Oct 15).',
    source: 'EMS HRM Module · Live Leave Register',
  },
  'who_late': {
    answer: 'Today 2 employees checked in past the grace cut-off: Tariq Mehmood (09:14, 4 min late) and Ava Chen (09:18, 8 min late).',
    source: 'EMS Room Engine · Attendance Feed',
  },
};

export function HrDashboardPage() {
  const session = getSession();
  const toast = useToast();
  const userName = session?.user.name ?? 'Hina Shah';
  const firstName = userName.split(' ')[0] || 'Hina';

  const [employees, setEmployees] = useState(DEMO_DIRECTORY);
  const [leaveRequests, setLeaveRequests] = useState(INITIAL_LEAVE_REQUESTS);
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  
  // HR Agent state
  const [selectedQuestion, setSelectedQuestion] = useState('late_arrival');
  const [agentAnswer, setAgentAnswer] = useState(HR_AGENT_KNOWLEDGE['late_arrival']);

  function handleLeaveAction(id: string, action: 'approved' | 'rejected') {
    setLeaveRequests((prev) =>
      prev.map((req) => (req.id === id ? { ...req, status: action } : req))
    );
    const item = leaveRequests.find((r) => r.id === id);
    toast.notify(`Leave request for ${item?.name} has been ${action}.`);
  }

  function handleEmployeeAdded(newEmp: NewEmployeeData) {
    setEmployees((prev) => [
      {
        id: newEmp.id,
        name: newEmp.name,
        email: newEmp.email,
        role: newEmp.role,
        department: newEmp.department,
        status: newEmp.status,
      },
      ...prev,
    ]);
  }

  function askAgent(key: string) {
    setSelectedQuestion(key);
    setAgentAnswer(HR_AGENT_KNOWLEDGE[key]);
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            HR People Dashboard
            <DemoBadge />
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            Directory, attendance logs, leave decisions, and rule-based HR Agent. Welcome back, {firstName}!
          </p>
        </div>
        <div className="sm:w-44">
          <Button type="button" onClick={() => setIsAddModalOpen(true)}>
            + Add Employee
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Total Headcount</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">{employees.length + 32}</p>
          <p className="mt-1 text-xs font-semibold text-success-text">+3 new hires this month</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Present Today</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">38 / 42</p>
          <p className="mt-1 text-xs text-ink-muted">90.5% attendance rate</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">On Approved Leave</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">02</p>
          <p className="mt-1 text-xs text-ink-muted">1 annual · 1 casual</p>
        </div>
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">Pending Decisions</p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            {leaveRequests.filter((r) => r.status === 'pending').length}
          </p>
          <p className="mt-1 text-xs font-semibold text-warning-text">Awaiting your approval</p>
        </div>
      </div>

      {/* Main Grid: Pending Leave & HR Agent */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
        {/* Left Column: Pending Leave Decisions */}
        <section aria-labelledby="leave-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 id="leave-heading" className="text-[15px] font-bold text-ink">Leave Requests & Approvals</h2>
              <p className="mt-0.5 text-xs text-ink-muted">Review team requests according to company leave allowances</p>
            </div>
            <span className="rounded-full bg-info-bg px-2.5 py-1 text-[11px] font-semibold text-info-text">
              {leaveRequests.filter((r) => r.status === 'pending').length} Actionable
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {leaveRequests.map((req) => (
              <div key={req.id} className="rounded-xl border border-line-soft p-4 transition-colors hover:border-line">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <span className="font-bold text-ink">{req.name}</span>
                    <span className="ml-2 text-xs text-ink-muted">· {req.role}</span>
                    <p className="mt-1 text-xs font-medium text-ink-body">
                      <span className="font-semibold text-accent">{req.type}</span> ({req.days}) : {req.dates}
                    </p>
                    <p className="mt-1 text-xs italic text-ink-muted">&ldquo;{req.reason}&rdquo;</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-2">
                    {req.status === 'pending' ? (
                      <>
                        <button
                          type="button"
                          onClick={() => handleLeaveAction(req.id, 'approved')}
                          className="rounded-lg bg-success-bg px-3 py-1.5 text-xs font-bold text-success-text hover:bg-success hover:text-white"
                        >
                          Approve
                        </button>
                        <button
                          type="button"
                          onClick={() => handleLeaveAction(req.id, 'rejected')}
                          className="rounded-lg bg-danger-soft px-3 py-1.5 text-xs font-bold text-danger hover:bg-danger hover:text-white"
                        >
                          Decline
                        </button>
                      </>
                    ) : (
                      <Badge tone={req.status === 'approved' ? 'success' : 'danger'}>
                        {req.status === 'approved' ? 'Approved' : 'Declined'}
                      </Badge>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Right Column: Rule-based HR Agent (engine/hr_agent.py) */}
        <section aria-labelledby="agent-heading" className="rounded-card bg-card p-5 shadow-card sm:p-6">
          <div className="flex items-center gap-2">
            <span className="flex size-7 items-center justify-center rounded-lg bg-purple-bg text-sm font-bold text-purple-text">
              AI
            </span>
            <div>
              <h2 id="agent-heading" className="text-[15px] font-bold text-ink">HR Policy Agent</h2>
              <p className="text-[11px] text-ink-muted">Rule-based, 100% explainable (DEC-007)</p>
            </div>
          </div>

          <p className="mt-3 text-xs text-ink-muted">Select a question to consult company records:</p>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {[
              { id: 'late_arrival', label: 'Late grace rule?' },
              { id: 'leave_balance', label: 'Annual allowance?' },
              { id: 'who_on_leave', label: 'Who is on leave?' },
              { id: 'who_late', label: 'Who was late today?' },
            ].map((q) => (
              <button
                key={q.id}
                type="button"
                onClick={() => askAgent(q.id)}
                className={`rounded-lg px-2.5 py-1 text-[11px] font-semibold transition-colors ${
                  selectedQuestion === q.id
                    ? 'bg-accent text-white'
                    : 'bg-search-bg text-ink hover:bg-nav-active'
                }`}
              >
                {q.label}
              </button>
            ))}
          </div>

          <div className="mt-4 rounded-xl border border-line-soft bg-panel-from p-3.5">
            <p className="text-[11px] font-bold tracking-wider text-accent uppercase">Verified Answer</p>
            <p className="mt-1.5 text-xs leading-relaxed text-ink-body">{agentAnswer.answer}</p>
            <div className="mt-2.5 border-t border-line-soft pt-2">
              <span className="text-[10px] font-semibold text-ink-muted">Source: {agentAnswer.source}</span>
            </div>
          </div>
        </section>
      </div>

      {/* Employee Directory Quick Table */}
      <section aria-labelledby="directory-heading" className="mt-4 rounded-card bg-card p-5 shadow-card sm:p-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 id="directory-heading" className="text-[15px] font-bold text-ink">Active Employee Directory</h2>
            <p className="mt-0.5 text-xs text-ink-muted">Current team records and assigned roles</p>
          </div>
          <span className="text-xs font-semibold text-ink-muted">{employees.length} team members</span>
        </div>

        <div className="mt-4 overflow-x-auto rounded-xl border border-line-soft">
          <table className="w-full min-w-[560px] text-left text-sm">
            <thead>
              <tr className="bg-panel-from text-xs text-ink-muted uppercase">
                <th scope="col" className="px-4 py-3 font-semibold">Name & Email</th>
                <th scope="col" className="px-4 py-3 font-semibold">Role</th>
                <th scope="col" className="px-4 py-3 font-semibold">Department</th>
                <th scope="col" className="px-4 py-3 font-semibold">Status</th>
              </tr>
            </thead>
            <tbody>
              {employees.slice(0, 6).map((member) => (
                <tr key={member.id} className="border-t border-line-soft">
                  <td className="px-4 py-3">
                    <span className="block font-bold text-ink">{member.name}</span>
                    <span className="block text-xs text-ink-muted">{member.email}</span>
                  </td>
                  <td className="px-4 py-3 text-ink-body">{member.role}</td>
                  <td className="px-4 py-3 text-ink-body">{member.department}</td>
                  <td className="px-4 py-3">
                    <Badge tone={member.status === 'Active' ? 'success' : member.status === 'On leave' ? 'warning' : 'info'}>
                      {member.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      {/* Add Employee Modal */}
      <AddEmployeeModal
        open={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onAdded={handleEmployeeAdded}
      />
    </div>
  );
}
