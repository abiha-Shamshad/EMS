
import { useState, type FormEvent } from 'react';

import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { DemoBadge } from '@/components/ui/DemoBadge';
import { Modal } from '@/components/ui/Modal';
import { TextField } from '@/components/ui/TextField';
import { Textarea } from '@/components/ui/Textarea';
import { useToast } from '@/components/ui/Toast';
import { getSession } from '@/lib/session';

// Inline calendar icon (data-URI SVG) for the TextField icon prop which expects an img src.
const CALENDAR_ICON =
  'data:image/svg+xml;utf8,' +
  encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#5d6b8f" stroke-width="1.8" stroke-linecap="round"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>`,
  );


interface MyTask {
  id: string;
  title: string;
  project: string;
  stage: 'todo' | 'active' | 'review' | 'done';
}

interface LeaveHistoryItem {
  id: string;
  type: string;
  dates: string;
  status: string;
}

const MY_INITIAL_TASKS: MyTask[] = [
  {
    id: 'mt-1',
    title: 'Write Auth and Session Token unit tests',
    project: 'Core Platform',
    stage: 'active',
  },
  {
    id: 'mt-2',
    title: 'Implement Chrome Extension heartbeat listener',
    project: 'Live Room Extension',
    stage: 'todo',
  },
  {
    id: 'mt-3',
    title: 'Document OpenAPI spec examples',
    project: 'Contracts',
    stage: 'review',
  },
];

const AUDITED_VIEWERS = [
  {
    id: 'v-1',
    viewerName: 'Imran Qureshi (CEO)',
    reason: 'Sprint milestone sync & demo review',
    time: '10:45 AM today',
    duration: '4 min',
  },
  {
    id: 'v-2',
    viewerName: 'Nadia Khan (COO)',
    reason: 'Operations & task workflow review',
    time: 'Yesterday 3:15 PM',
    duration: '6 min',
  },
];

export function EmployeeDashboardPage() {
  const session = getSession();
  const toast = useToast();

  const userName = session?.user.name ?? 'Bilal Ahmed';
  const firstName = userName.split(' ')[0] || 'Bilal';

  // Work session state
  const [isCheckedIn, setIsCheckedIn] = useState(true);
  const [presenceState, setPresenceState] = useState<'Active' | 'On break'>(
    'Active',
  );
  const [myTasks, setMyTasks] = useState<MyTask[]>(MY_INITIAL_TASKS);

  // Leave request modal state
  const [isLeaveModalOpen, setIsLeaveModalOpen] = useState(false);
  const [leaveType, setLeaveType] = useState('Annual');
  const [leaveDates, setLeaveDates] = useState('');
  const [leaveReason, setLeaveReason] = useState('');

  const [leaveHistory, setLeaveHistory] = useState<LeaveHistoryItem[]>([
    {
      id: 'lh-1',
      type: 'Casual Leave',
      dates: 'Sep 24, 2026',
      status: 'Approved',
    },
    {
      id: 'lh-2',
      type: 'Annual Leave',
      dates: 'Aug 10 - Aug 12, 2026',
      status: 'Approved',
    },
  ]);

  function toggleCheckIn() {
    if (isCheckedIn) {
      setIsCheckedIn(false);
      setPresenceState('Active');
      toast.notify('Checked out successfully. Work session recorded.');
    } else {
      setIsCheckedIn(true);
      setPresenceState('Active');
      toast.notify('Checked in. Work session started on selected task.');
    }
  }

  function toggleBreak() {
    if (!isCheckedIn) {
      toast.notify('Please check in before taking a break.', 'error');
      return;
    }

    if (presenceState === 'Active') {
      setPresenceState('On break');
      toast.notify('Break started. Screen sharing paused automatically.');
    } else {
      setPresenceState('Active');
      toast.notify('Break ended. You are back to Active.');
    }
  }

  function handleTaskProgress(id: string) {
    setMyTasks((previousTasks) =>
      previousTasks.map((task) => {
        if (task.id !== id) {
          return task;
        }

        const nextStage: MyTask['stage'] =
          task.stage === 'todo'
            ? 'active'
            : task.stage === 'active'
              ? 'review'
              : 'done';

        return { ...task, stage: nextStage };
      }),
    );

    toast.notify('Task stage updated.');
  }

  function handleLeaveSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!leaveDates.trim() || !leaveReason.trim()) {
      toast.notify(
        'Please provide dates and a reason for your leave.',
        'error',
      );
      return;
    }

    setLeaveHistory((previousHistory) => [
      {
        id: `lh-${Date.now()}`,
        type: `${leaveType} Leave`,
        dates: leaveDates.trim(),
        status: 'Pending Approval',
      },
      ...previousHistory,
    ]);

    toast.notify('Leave request submitted to your manager.');

    setIsLeaveModalOpen(false);
    setLeaveDates('');
    setLeaveReason('');
    setLeaveType('Annual');
  }

  return (
    <div>
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="flex flex-wrap items-center gap-2 text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            My Workspace
            <DemoBadge />
          </h1>

          <p className="mt-0.5 text-[13px] text-ink-muted">
            Personal work session, presence status, assigned tasks, and
            transparency log. Welcome back, {firstName}!
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <Button
            type="button"
            variant={isCheckedIn ? 'outline' : 'primary'}
            onClick={toggleCheckIn}
          >
            {isCheckedIn ? 'Check Out' : 'Check In'}
          </Button>

          {isCheckedIn && (
            <Button
              type="button"
              variant="outline"
              onClick={toggleBreak}
            >
              {presenceState === 'Active' ? 'Take a Break' : 'Resume Work'}
            </Button>
          )}
        </div>
      </div>

      {/* KPI Cards */}
      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">
            My Session Status
          </p>

          <div className="mt-2 flex items-center gap-2">
            <span
              className={`size-2.5 rounded-full ${!isCheckedIn
                ? 'bg-danger'
                : presenceState === 'Active'
                  ? 'bg-success'
                  : 'bg-warning'
                }`}
            />

            <span className="text-xl font-extrabold text-ink">
              {!isCheckedIn ? 'Checked Out' : presenceState}
            </span>
          </div>

          <p className="mt-1 text-xs text-ink-muted">
            {isCheckedIn ? 'Work session in progress' : 'No active session'}
          </p>
        </div>

        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">
            Daily Break Used
          </p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            18 / 45m
          </p>
          <p className="mt-1 text-xs text-success-text">
            27 minutes remaining
          </p>
        </div>

        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">
            Annual Leave Balance
          </p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            14 Days
          </p>
          <p className="mt-1 text-xs text-ink-muted">
            4 days used this year
          </p>
        </div>

        <div className="rounded-card bg-card p-5 shadow-card">
          <p className="text-[13px] font-semibold text-ink-muted">
            Assigned Tasks
          </p>
          <p className="mt-2 text-[28px] font-extrabold tracking-tight text-ink">
            {myTasks.filter((task) => task.stage !== 'done').length}
          </p>
          <p className="mt-1 text-xs text-info-text">
            {myTasks.filter((task) => task.stage === 'active').length} in active
            progress
          </p>
        </div>
      </div>

      {/* Privacy Banner */}
      <div className="mt-4 flex items-center gap-3 rounded-2xl border border-line-soft bg-info-bg/40 p-4 text-xs text-ink-body">
        <span className="flex size-7 shrink-0 items-center justify-center rounded-lg bg-primary font-bold text-white">
          ✓
        </span>

        <p>
          <span className="font-bold text-ink">Privacy Guarantee:</span> EMS
          Room never tracks keystrokes, URLs, browser history, webcam,
          microphone, or screenshots. Screen sharing requires your explicit
          action and browser permission.
        </p>
      </div>

      {/* Main Grid */}
      <div className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[1fr_380px]">
        {/* My Assigned Tasks */}
        <section
          aria-labelledby="my-tasks-heading"
          className="rounded-card bg-card p-5 shadow-card sm:p-6"
        >
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2
                id="my-tasks-heading"
                className="text-[15px] font-bold text-ink"
              >
                My Assigned Tasks
              </h2>
              <p className="mt-0.5 text-xs text-ink-muted">
                Update your task status as you make progress
              </p>
            </div>

            <span className="text-xs font-semibold text-ink-muted">
              {myTasks.length} tasks
            </span>
          </div>

          <div className="mt-4 space-y-3">
            {myTasks.map((task) => (
              <div
                key={task.id}
                className="rounded-xl border border-line-soft p-4"
              >
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="font-bold text-ink">{task.title}</p>
                    <p className="mt-0.5 text-xs text-ink-muted">
                      Project: {task.project}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center gap-2">
                    <Badge
                      tone={
                        task.stage === 'done'
                          ? 'success'
                          : task.stage === 'active'
                            ? 'info'
                            : task.stage === 'review'
                              ? 'purple'
                              : 'neutral'
                      }
                    >
                      {task.stage.toUpperCase()}
                    </Badge>

                    {task.stage !== 'done' && (
                      <button
                        type="button"
                        onClick={() => handleTaskProgress(task.id)}
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

        {/* Transparency Log and Leave History */}
        <div className="space-y-4">
          <section
            aria-labelledby="viewers-heading"
            className="rounded-card bg-card p-5 shadow-card sm:p-6"
          >
            <h2
              id="viewers-heading"
              className="text-[15px] font-bold text-ink"
            >
              Who Viewed My Screen
            </h2>

            <p className="mt-0.5 text-xs text-ink-muted">
              Screen-viewing audit log. Entries should come from the actual
              audit source.
            </p>

            <div className="mt-4 space-y-3">
              {AUDITED_VIEWERS.map((viewer) => (
                <div
                  key={viewer.id}
                  className="rounded-xl border border-line-soft p-3"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
                    <span className="font-bold text-ink">
                      {viewer.viewerName}
                    </span>
                    <span className="text-ink-muted">{viewer.time}</span>
                  </div>

                  <p className="mt-1 text-xs italic text-ink-body">
                    &ldquo;{viewer.reason}&rdquo;
                  </p>

                  <p className="mt-1 text-[11px] text-ink-muted">
                    Duration: {viewer.duration}
                  </p>
                </div>
              ))}
            </div>
          </section>

          <section
            aria-labelledby="my-leave-heading"
            className="rounded-card bg-card p-5 shadow-card sm:p-6"
          >
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h2
                  id="my-leave-heading"
                  className="text-[15px] font-bold text-ink"
                >
                  Leave &amp; Time Off
                </h2>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Request time off from your manager
                </p>
              </div>

              <Button
                type="button"
                variant="outline"
                onClick={() => setIsLeaveModalOpen(true)}
              >
                + Request Leave
              </Button>
            </div>

            <div className="mt-4 space-y-2">
              {leaveHistory.map((leave) => (
                <div
                  key={leave.id}
                  className="flex flex-col gap-2 rounded-lg bg-panel-from px-3 py-2 text-xs sm:flex-row sm:items-center sm:justify-between"
                >
                  <div>
                    <span className="font-bold text-ink">{leave.type}</span>
                    <span className="ml-2 text-ink-muted">{leave.dates}</span>
                  </div>

                  <Badge
                    tone={
                      leave.status === 'Approved'
                        ? 'success'
                        : 'warning'
                    }
                  >
                    {leave.status}
                  </Badge>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>

      {/* Leave Request Modal */}
      <Modal
        open={isLeaveModalOpen}
        title="Request Leave"
        description="Submit a leave application for approval by your manager."
        onClose={() => setIsLeaveModalOpen(false)}
      >
        <form onSubmit={handleLeaveSubmit} className="mt-3 space-y-4">
          <label className="block space-y-1.5">
            <span className="text-sm font-semibold text-ink">
              Leave Type
            </span>

            <select
              value={leaveType}
              onChange={(event) => setLeaveType(event.target.value)}
              className="w-full rounded-xl border border-line-soft bg-card px-3 py-2.5 text-sm text-ink outline-none transition focus:border-primary focus:ring-2 focus:ring-primary/15"
            >
              <option value="Annual">
                Annual Leave (14 days available)
              </option>
              <option value="Casual">
                Casual Leave (6 days available)
              </option>
              <option value="Sick">Sick Leave (8 days available)</option>
              <option value="Unpaid">Unpaid Leave</option>
            </select>
          </label>


          <TextField
            label="Dates / Duration"
            icon={CALENDAR_ICON}
            placeholder="e.g. Oct 24 - Oct 26 (3 working days)"
            value={leaveDates}
            onChange={(event) => setLeaveDates(event.target.value)}
            required
          />


          <Textarea
            label="Reason for Leave"
            placeholder="Please provide a brief reason..."
            value={leaveReason}
            onChange={(event) => setLeaveReason(event.target.value)}
            required
          />

          <div className="mt-5 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsLeaveModalOpen(false)}
            >
              Cancel
            </Button>

            <Button type="submit">Submit Request</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
