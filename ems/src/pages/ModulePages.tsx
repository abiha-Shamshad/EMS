
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import {
  AddEmployeeModal,
  type NewEmployeeData,
} from '@/components/hr/AddEmployeeModal';
import { Avatar } from '@/components/ui/Avatar';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { EmptyState, LoadingState } from '@/components/ui/StateBlocks';
import { DEMO_DIRECTORY, DEMO_PROJECTS } from '@/demo/fixtures';

/**
 * Shared shell for module pages.
 */
function ModuleShell({
  title,
  description,
  action,
  children,
}: {
  title: string;
  description: string;
  action?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-xl font-extrabold tracking-tight text-ink sm:text-2xl">
            {title}
          </h1>
          <p className="mt-0.5 text-[13px] text-ink-muted">
            {description}
          </p>
        </div>
        {action}
      </div>
      <div className="mt-4">{children}</div>
    </div>
  );
}

function Card({
  children,
  className = '',
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={`rounded-card bg-card p-5 shadow-card sm:p-6 ${className}`}>
      {children}
    </div>
  );
}

/**
 * Employee monitoring module.
 */
export function MonitoringPage() {
  const [loading] = useState(false);

  if (loading) {
    return <LoadingState label="Loading live presence…" />;
  }

  return (
    <ModuleShell
      title="Employee Monitoring"
      description="Live presence across your company. Demo data — connect the backend for live status."
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {DEMO_DIRECTORY.slice(0, 6).map((member) => (
          <Card key={member.id}>
            <div className="flex items-center gap-3">
              <Avatar name={member.name} />

              <div className="min-w-0">
                <p className="truncate text-sm font-bold text-ink">
                  {member.name}
                </p>
                <p className="truncate text-xs text-ink-muted">
                  {member.department}
                </p>
              </div>

              <span className="ml-auto">
                <Badge
                  tone={
                    member.status === 'Active'
                      ? 'success'
                      : member.status === 'On leave'
                        ? 'warning'
                        : 'info'
                  }
                >
                  {member.status}
                </Badge>
              </span>
            </div>
          </Card>
        ))}
      </div>
    </ModuleShell>
  );
}

/**
 * FIX:
 * The Add Employee modal can return "Offline", while the original
 * DEMO_DIRECTORY status type only allows "Active", "On leave", and "Invited".
 *
 * This page-specific type supports all four statuses without modifying
 * the shared demo fixtures or other modules.
 */
type HrDirectoryMember = Omit<
  (typeof DEMO_DIRECTORY)[number],
  'status'
> & {
  status: 'Active' | 'On leave' | 'Invited' | 'Offline';
};

/**
 * HR Management and Employee Directory.
 */
export function HrPage() {
  const [query, setQuery] = useState('');
  const [directory, setDirectory] =
    useState<HrDirectoryMember[]>(DEMO_DIRECTORY);
  const [isAddOpen, setIsAddOpen] = useState(false);

  const members = useMemo(
    () =>
      directory.filter((member) =>
        `${member.name} ${member.department} ${member.role}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [directory, query],
  );

  function handleAdded(newEmp: NewEmployeeData) {
    const newMember: HrDirectoryMember = {
      id: newEmp.id,
      name: newEmp.name,
      email: newEmp.email,
      role: newEmp.role,
      department: newEmp.department,
      status: newEmp.status,
    };

    setDirectory((previous) => [newMember, ...previous]);
  }

  return (
    <ModuleShell
      title="HR Management"
      description="Directory, attendance and leave. Real-time team roster."
      action={
        <div className="sm:w-52">
          <Button type="button" onClick={() => setIsAddOpen(true)}>
            Add employee
          </Button>
        </div>
      }
    >
      <Card>
        <form
          role="search"
          onSubmit={(event) => event.preventDefault()}
          className="max-w-sm"
        >
          <label htmlFor="hr-search" className="sr-only">
            Search employees
          </label>

          <input
            id="hr-search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search name, role, department…"
            className="h-11 w-full rounded-xl border border-line bg-white px-4 text-sm text-ink placeholder:text-placeholder focus:border-accent focus:ring-4 focus:ring-accent/15 focus:outline-none"
          />
        </form>

        {members.length === 0 ? (
          <div className="mt-4">
            <EmptyState title="No employees match">
              <p>Try a different search.</p>
            </EmptyState>
          </div>
        ) : (
          <div className="mt-4 overflow-x-auto rounded-xl border border-line-soft">
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="bg-panel-from text-xs text-ink-muted uppercase">
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Name
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Role
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Department
                  </th>
                  <th scope="col" className="px-4 py-3 font-semibold">
                    Status
                  </th>
                </tr>
              </thead>

              <tbody>
                {members.map((member) => (
                  <tr
                    key={member.id}
                    className="border-t border-line-soft"
                  >
                    <td className="px-4 py-3">
                      <span className="flex items-center gap-2.5">
                        <Avatar name={member.name} size="sm" />

                        <span>
                          <span className="block font-bold text-ink">
                            {member.name}
                          </span>
                          <span className="block text-xs text-ink-muted">
                            {member.email}
                          </span>
                        </span>
                      </span>
                    </td>

                    <td className="px-4 py-3 text-ink-body">
                      {member.role}
                    </td>

                    <td className="px-4 py-3 text-ink-body">
                      {member.department}
                    </td>

                    <td className="px-4 py-3">
                      <Badge
                        tone={
                          member.status === 'Active'
                            ? 'success'
                            : member.status === 'On leave'
                              ? 'warning'
                              : 'info'
                        }
                      >
                        {member.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <AddEmployeeModal
        open={isAddOpen}
        onClose={() => setIsAddOpen(false)}
        onAdded={handleAdded}
      />
    </ModuleShell>
  );
}

/**
 * Projects module.
 */
export function ProjectsPage() {
  return (
    <ModuleShell
      title="Projects"
      description="Delivery across every project. Demo data — connect the backend for live boards."
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        {DEMO_PROJECTS.map((project) => (
          <Card key={project.id}>
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="truncate text-[15px] font-bold text-ink">
                  {project.name}
                </p>
                <p className="text-xs text-ink-muted">
                  {project.client} · Due {project.due}
                </p>
              </div>

              <Badge
                tone={project.status === 'On track' ? 'success' : 'warning'}
              >
                {project.status}
              </Badge>
            </div>

            <div
              className="mt-3 h-2 overflow-hidden rounded-full bg-search-bg"
              role="img"
              aria-label={`${project.name} ${project.progress}% complete`}
            >
              <div
                className="h-full rounded-full bg-chart-line"
                style={{ width: `${project.progress}%` }}
              />
            </div>

            <p className="mt-2 text-xs font-semibold text-ink">
              {project.progress}% complete
            </p>
          </Card>
        ))}
      </div>
    </ModuleShell>
  );
}

/**
 * Shared placeholder for modules whose backend is not yet connected.
 */
function ComingSoonCard({
  name,
  backPath = '/app/dashboard',
}: {
  name: string;
  backPath?: string;
}) {
  return (
    <Card>
      <EmptyState title={`${name} is coming next`}>
        <p>
          This module follows the same shell, tokens and states as the
          dashboard. It will be available once its backend contract is
          connected.{' '}
          <Link
            to={backPath}
            className="font-semibold text-primary hover:underline"
          >
            Back to dashboard
          </Link>
        </p>
      </EmptyState>
    </Card>
  );
}

// ── CTO module pages ───────────────────────────────────────────────

export function SystemHealthPage() {
  return (
    <ModuleShell
      title="System Health"
      description="Platform service status, uptime and latency monitoring."
    >
      <ComingSoonCard
        name="System Health"
        backPath="/app/cto-dashboard"
      />
    </ModuleShell>
  );
}

export function DeploymentsPage() {
  return (
    <ModuleShell
      title="Deployments"
      description="Release pipeline, deployment history and CI/CD status."
    >
      <ComingSoonCard
        name="Deployments"
        backPath="/app/cto-dashboard"
      />
    </ModuleShell>
  );
}

export function IncidentsPage() {
  return (
    <ModuleShell
      title="Incidents & Alerts"
      description="Open incidents, escalations and resolution tracking."
    >
      <ComingSoonCard
        name="Incidents & Alerts"
        backPath="/app/cto-dashboard"
      />
    </ModuleShell>
  );
}

export function DocumentationPage() {
  return (
    <ModuleShell
      title="Documentation"
      description="Engineering docs, runbooks and API references."
    >
      <ComingSoonCard
        name="Documentation"
        backPath="/app/cto-dashboard"
      />
    </ModuleShell>
  );
}

// ── CFO module pages ───────────────────────────────────────────────

export function FinancialOverviewPage() {
  return (
    <ModuleShell
      title="Financial Overview"
      description="High-level financial health snapshot across the company."
    >
      <ComingSoonCard
        name="Financial Overview"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function RevenueExpensesPage() {
  return (
    <ModuleShell
      title="Revenue & Expenses"
      description="Detailed revenue and cost breakdown by period."
    >
      <ComingSoonCard
        name="Revenue & Expenses"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function BudgetsPage() {
  return (
    <ModuleShell
      title="Budgets"
      description="Departmental budget allocations and utilisation tracking."
    >
      <ComingSoonCard
        name="Budgets"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function PayrollSummaryPage() {
  return (
    <ModuleShell
      title="Payroll Summary"
      description="Payroll cycles, headcount costs and upcoming obligations."
    >
      <ComingSoonCard
        name="Payroll Summary"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function InvoicesPage() {
  return (
    <ModuleShell
      title="Invoices & Payments"
      description="Outstanding invoices, payment status and collections."
    >
      <ComingSoonCard
        name="Invoices & Payments"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function ForecastingPage() {
  return (
    <ModuleShell
      title="Forecasting"
      description="Revenue and expense projections for future periods."
    >
      <ComingSoonCard
        name="Forecasting"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function FinancialReportsPage() {
  return (
    <ModuleShell
      title="Financial Reports"
      description="Exportable P&L, balance sheets and audit-ready summaries."
    >
      <ComingSoonCard
        name="Financial Reports"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

export function DepartmentsPage() {
  return (
    <ModuleShell
      title="Departments"
      description="Department-level cost centres, headcount and budgets."
    >
      <ComingSoonCard
        name="Departments"
        backPath="/app/cfo-dashboard"
      />
    </ModuleShell>
  );
}

// ── General module pages ───────────────────────────────────────────

export function CrmPage() {
  return (
    <ModuleShell
      title="CRM"
      description="Pipeline and client lifecycle."
    >
      <ComingSoonCard name="CRM" />
    </ModuleShell>
  );
}

export function LeadHunterPage() {
  return (
    <ModuleShell
      title="Lead Hunter"
      description="Find your next customers."
    >
      <ComingSoonCard name="Lead Hunter" />
    </ModuleShell>
  );
}

export function AutomationsPage() {
  return (
    <ModuleShell
      title="Automations"
      description="Rules that run themselves."
    >
      <ComingSoonCard name="Automations" />
    </ModuleShell>
  );
}

export function ReportsPage() {
  return (
    <ModuleShell
      title="Reports & Analytics"
      description="Numbers leadership can trust."
    >
      <ComingSoonCard name="Reports & Analytics" />
    </ModuleShell>
  );
}

export function UsersPage() {
  return (
    <ModuleShell
      title="Users & Roles"
      description="Roles and team access."
    >
      <ComingSoonCard name="Users & Roles" />
    </ModuleShell>
  );
}

export function IntegrationsPage() {
  return (
    <ModuleShell
      title="Integrations"
      description="Connected tools."
    >
      <ComingSoonCard name="Integrations" />
    </ModuleShell>
  );
}

export function SettingsPage() {
  return (
    <ModuleShell
      title="Settings"
      description="Company preferences."
    >
      <ComingSoonCard name="Settings" />
    </ModuleShell>
  );
}
