import { NavLink } from 'react-router-dom';
import { BrandLogo } from '@/components/BrandLogo';
import { getSession } from '@/lib/session';
import { Role } from '@/lib/enums';
import {
  AutomationsIcon,
  CrmIcon,
  DashboardIcon,
  HrIcon,
  IntegrationsIcon,
  LeadHunterIcon,
  MonitoringIcon,
  ProjectsIcon,
  ReportsIcon,
  SettingsIcon,
  UsersIcon,
} from './icons';
import type { SVGProps } from 'react';

export interface NavItem {
  to: string;
  label: string;
  icon: (props: { className?: string }) => React.JSX.Element;
  roles?: Role[]; // if set, only shown to these roles
}

/* ── Inline icons for role-specific dashboards & new modules ─────────── */
function CtoDashIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
      <polyline points="16 18 22 12 16 6" /><polyline points="8 6 2 12 8 18" />
    </svg>
  );
}
function CfoDashIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth={1.8} strokeLinecap="round">
      <line x1="12" y1="1" x2="12" y2="23" /><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
    </svg>
  );
}
function ServerIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <rect x="3" y="4" width="14" height="5" rx="1.5" /><rect x="3" y="11" width="14" height="5" rx="1.5" />
      <path d="M6.5 6.5h.01M6.5 13.5h.01" />
    </svg>
  );
}
function CloudUpIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <polyline points="13 9 10 6 7 9" /><line x1="10" y1="6" x2="10" y2="14" />
      <path d="M15.5 14a4 4 0 1 0-2.5-7.07A4.5 4.5 0 1 0 4.5 14" />
    </svg>
  );
}
function AlertTriIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <path d="M9.07 3.35 2.18 15A1 1 0 0 0 3 16.5h13.95a1 1 0 0 0 .87-1.5L10.93 3.35a1 1 0 0 0-1.86 0Z" />
      <line x1="10" y1="9" x2="10" y2="12" /><line x1="10" y1="14.5" x2="10.01" y2="14.5" />
    </svg>
  );
}
function ApiIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <rect x="3" y="3" width="5.5" height="5.5" rx="1.2" /><rect x="11.5" y="3" width="5.5" height="5.5" rx="1.2" />
      <rect x="3" y="11.5" width="5.5" height="5.5" rx="1.2" /><path d="M14.2 11.5v5.5M11.5 14.2h5.5" />
    </svg>
  );
}
function BookIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <path d="M4 3h8a2 2 0 0 1 2 2v12H4a2 2 0 0 1 0-4h10" /><path d="M8 3v8l2.5-2 2.5 2V3" />
    </svg>
  );
}
function TrendUpIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <polyline points="4 14 8 10 11 13 16 7" /><polyline points="13 7 16 7 16 10" />
    </svg>
  );
}
function WalletIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <rect x="2" y="5" width="16" height="12" rx="2" /><path d="M2 9h16" /><circle cx="15" cy="13.5" r="1" fill="currentColor" stroke="none" />
    </svg>
  );
}
function ReceiptIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <path d="M5 2h10v16l-2.5-2-2.5 2-2.5-2L5 18V2Z" /><line x1="8" y1="7" x2="12" y2="7" /><line x1="8" y1="10" x2="12" y2="10" />
    </svg>
  );
}
function PayrollIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <circle cx="10" cy="8" r="4" /><path d="M3.5 17c.8-3 3.5-5 6.5-5s5.7 2 6.5 5" /><line x1="10" y1="6" x2="10" y2="10" />
    </svg>
  );
}
function ForecastIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <path d="M4 16.5h13M6.5 16.5v-7M10.5 16.5v-11M14.5 16.5v-5" strokeDasharray="0" />
      <path d="M5 11.5c2-1 3 1 5-2s3.5-1 5-4" strokeDasharray="3 2" />
    </svg>
  );
}
function BuildingIcon(p: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" aria-hidden focusable={false} {...p}>
      <rect x="3" y="3" width="14" height="14" rx="1.5" /><path d="M3 8h14M8 8v9M12 8v9" />
    </svg>
  );
}

/* ── Role-specific nav definitions ──────────────────────────────────── */

/** CEO: full platform overview modules. */
const CEO_WORKSPACE: NavItem[] = [
  { to: '/app/dashboard',   label: 'CEO Dashboard',       icon: (p) => <DashboardIcon {...p} /> },
  { to: '/app/monitoring',  label: 'Employee Monitoring',  icon: (p) => <MonitoringIcon {...p} /> },
  { to: '/app/hr',          label: 'HR Management',        icon: (p) => <HrIcon {...p} /> },
  { to: '/app/projects',    label: 'Projects & Tasks',     icon: (p) => <ProjectsIcon {...p} /> },
  { to: '/app/crm',         label: 'CRM & Pipeline',       icon: (p) => <CrmIcon {...p} /> },
  { to: '/app/lead-hunter', label: 'Lead Hunter',          icon: (p) => <LeadHunterIcon {...p} /> },
  { to: '/app/automations', label: 'Automations',          icon: (p) => <AutomationsIcon {...p} /> },
  { to: '/app/reports',     label: 'Reports & Analytics',  icon: (p) => <ReportsIcon {...p} /> },
];
const CEO_ADMIN: NavItem[] = [
  { to: '/app/users',       label: 'Users & Roles',  icon: (p) => <UsersIcon {...p} /> },
  { to: '/app/integrations',label: 'Integrations',   icon: (p) => <IntegrationsIcon {...p} /> },
  { to: '/app/settings',    label: 'Settings',        icon: (p) => <SettingsIcon {...p} /> },
];

/** CTO: engineering + platform modules (R1 permission: projectsManage, rulesManage). */
const CTO_WORKSPACE: NavItem[] = [
  { to: '/app/cto-dashboard', label: 'CTO Dashboard',       icon: (p) => <CtoDashIcon {...p} /> },
  { to: '/app/projects',      label: 'Engineering Projects', icon: (p) => <ProjectsIcon {...p} /> },
  { to: '/app/system-health', label: 'System Health',        icon: (p) => <ServerIcon {...p} /> },
  { to: '/app/deployments',   label: 'Deployments',          icon: (p) => <CloudUpIcon {...p} /> },
  { to: '/app/incidents',     label: 'Incidents & Alerts',   icon: (p) => <AlertTriIcon {...p} /> },
  { to: '/app/integrations',  label: 'Integrations & APIs',  icon: (p) => <ApiIcon {...p} /> },
  { to: '/app/reports',       label: 'Reports & Analytics',  icon: (p) => <ReportsIcon {...p} /> },
  { to: '/app/users',         label: 'Team & Roles',         icon: (p) => <UsersIcon {...p} /> },
  { to: '/app/documentation', label: 'Documentation',        icon: (p) => <BookIcon {...p} /> },
  { to: '/app/settings',      label: 'Settings',             icon: (p) => <SettingsIcon {...p} /> },
];

/** CFO: finance-specific modules (R1 permission: financeManage, leakageRead). */
const CFO_WORKSPACE: NavItem[] = [
  { to: '/app/cfo-dashboard',      label: 'CFO Dashboard',      icon: (p) => <CfoDashIcon {...p} /> },
  { to: '/app/financial-overview', label: 'Financial Overview', icon: (p) => <TrendUpIcon {...p} /> },
  { to: '/app/revenue-expenses',   label: 'Revenue & Expenses', icon: (p) => <WalletIcon {...p} /> },
  { to: '/app/budgets',            label: 'Budgets',            icon: (p) => <ReportsIcon {...p} /> },
  { to: '/app/payroll-summary',    label: 'Payroll Summary',    icon: (p) => <PayrollIcon {...p} /> },
  { to: '/app/invoices',           label: 'Invoices & Payments',icon: (p) => <ReceiptIcon {...p} /> },
  { to: '/app/forecasting',        label: 'Forecasting',        icon: (p) => <ForecastIcon {...p} /> },
  { to: '/app/financial-reports',  label: 'Financial Reports',  icon: (p) => <ReportsIcon {...p} /> },
  { to: '/app/departments',        label: 'Departments',        icon: (p) => <BuildingIcon {...p} /> },
  { to: '/app/settings',           label: 'Settings',           icon: (p) => <SettingsIcon {...p} /> },
];

/** COO: operations-wide access. */
const COO_WORKSPACE: NavItem[] = [
  { to: '/app/coo-dashboard', label: 'COO Dashboard',        icon: (p) => <DashboardIcon {...p} /> },
  { to: '/app/monitoring',    label: 'Employee Monitoring',   icon: (p) => <MonitoringIcon {...p} /> },
  { to: '/app/hr',            label: 'HR Management',         icon: (p) => <HrIcon {...p} /> },
  { to: '/app/projects',      label: 'Projects & Tasks',      icon: (p) => <ProjectsIcon {...p} /> },
  { to: '/app/crm',           label: 'CRM & Pipeline',        icon: (p) => <CrmIcon {...p} /> },
  { to: '/app/lead-hunter',   label: 'Lead Hunter',           icon: (p) => <LeadHunterIcon {...p} /> },
  { to: '/app/automations',   label: 'Automations',           icon: (p) => <AutomationsIcon {...p} /> },
  { to: '/app/reports',       label: 'Reports & Analytics',   icon: (p) => <ReportsIcon {...p} /> },
];
const COO_ADMIN: NavItem[] = [
  { to: '/app/integrations', label: 'Integrations', icon: (p) => <IntegrationsIcon {...p} /> },
  { to: '/app/settings',     label: 'Settings',     icon: (p) => <SettingsIcon {...p} /> },
];

/** HR: people & leave management. */
const HR_WORKSPACE: NavItem[] = [
  { to: '/app/hr-dashboard', label: 'HR Dashboard',    icon: (p) => <HrIcon {...p} /> },
  { to: '/app/hr',           label: 'HR Management',   icon: (p) => <HrIcon {...p} /> },
];
const HR_ADMIN: NavItem[] = [
  { to: '/app/users',    label: 'Users & Roles', icon: (p) => <UsersIcon {...p} /> },
  { to: '/app/settings', label: 'Settings',      icon: (p) => <SettingsIcon {...p} /> },
];

/** Manager: team tasks, CRM, lead hunter. */
const MANAGER_WORKSPACE: NavItem[] = [
  { to: '/app/manager-dashboard', label: 'Manager Dashboard', icon: (p) => <DashboardIcon {...p} /> },
  { to: '/app/hr',                label: 'HR Management',     icon: (p) => <HrIcon {...p} /> },
  { to: '/app/projects',          label: 'Projects & Tasks',  icon: (p) => <ProjectsIcon {...p} /> },
  { to: '/app/crm',               label: 'CRM & Pipeline',    icon: (p) => <CrmIcon {...p} /> },
  { to: '/app/lead-hunter',       label: 'Lead Hunter',       icon: (p) => <LeadHunterIcon {...p} /> },
  { to: '/app/settings',          label: 'Settings',          icon: (p) => <SettingsIcon {...p} /> },
];

/** Employee: personal workspace. */
const EMPLOYEE_WORKSPACE: NavItem[] = [
  { to: '/app/employee-dashboard', label: 'My Workspace',   icon: (p) => <DashboardIcon {...p} /> },
  { to: '/app/hr',                 label: 'HR Management',  icon: (p) => <HrIcon {...p} /> },
  { to: '/app/projects',           label: 'Projects',       icon: (p) => <ProjectsIcon {...p} /> },
  { to: '/app/settings',           label: 'Settings',       icon: (p) => <SettingsIcon {...p} /> },
];

/** Returns the [workspace, admin] nav groups for the current role. */
function navForRole(role: Role | null): { workspace: NavItem[]; admin: NavItem[] } {
  switch (role) {
    case Role.Cto: return { workspace: CTO_WORKSPACE, admin: [] };
    case Role.Cfo: return { workspace: CFO_WORKSPACE, admin: [] };
    case Role.Coo: return { workspace: COO_WORKSPACE, admin: COO_ADMIN };
    case Role.Hr:  return { workspace: HR_WORKSPACE,  admin: HR_ADMIN };
    case Role.Manager: return { workspace: MANAGER_WORKSPACE, admin: [] };
    case Role.Employee: return { workspace: EMPLOYEE_WORKSPACE, admin: [] };
    case Role.Ceo:
    default:
      return { workspace: CEO_WORKSPACE, admin: CEO_ADMIN };
  }
}

function NavSection({ title, items, onNavigate }: { title: string; items: NavItem[]; onNavigate?: () => void }) {
  if (items.length === 0) return null;
  return (
    <div>
      <p className="px-3 text-[11px] font-bold tracking-[0.08em] text-ink-muted uppercase">{title}</p>
      <ul className="mt-2 space-y-0.5">
        {items.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              end={item.to.endsWith('-dashboard') || item.to === '/app/dashboard'}
              onClick={onNavigate}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive ? 'bg-nav-active text-ink' : 'text-nav-ink hover:bg-nav-active/60'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span aria-hidden="true" className="absolute top-1/2 left-0 h-6 w-1 -translate-y-1/2 rounded-r-full bg-primary" />
                  )}
                  <item.icon className="size-5 shrink-0" />
                  <span className="min-w-0 truncate">{item.label}</span>
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SidebarBody({ onNavigate }: { onNavigate?: () => void }) {
  const session = getSession();
  const currentRole = session?.user.role ?? null;
  const { workspace, admin } = navForRole(currentRole);

  return (
    <div className="flex h-full flex-col">
      <div className="px-5 pt-6">
        <BrandLogo />
      </div>
      <nav aria-label="Primary" className="mt-8 flex-1 space-y-7 overflow-y-auto px-3 pb-6">
        <NavSection title="Workspace" items={workspace} onNavigate={onNavigate} />
        {admin.length > 0 && (
          <NavSection title="Administration" items={admin} onNavigate={onNavigate} />
        )}
      </nav>
      <div className="px-4 pb-6">
        <div className="rounded-2xl bg-nav-active p-4">
          <p className="flex items-center gap-2 text-sm font-bold text-ink">
            <span aria-hidden="true" className="flex size-5 items-center justify-center rounded-full bg-white text-xs text-primary shadow-chip">
              ?
            </span>
            Need help?
          </p>
          <p className="mt-1 text-xs text-ink-muted">Visit our help center</p>
          <a
            href="mailto:support@ems.example"
            className="mt-3 flex h-10 items-center justify-center rounded-xl bg-white text-[13px] font-semibold text-ink shadow-chip transition-colors hover:bg-panel-from"
          >
            Contact support
          </a>
        </div>
      </div>
    </div>
  );
}
