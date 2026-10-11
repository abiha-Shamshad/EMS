import { useEffect } from 'react';

export interface Crumb {
  label: string;
  to?: string;
}

const TITLES: Record<string, Crumb[]> = {
  '/app/dashboard':          [{ label: 'Workspace', to: '/app' }, { label: 'CEO Dashboard' }],
  '/app/cto-dashboard':      [{ label: 'Workspace', to: '/app' }, { label: 'Dashboards' }, { label: 'CTO Dashboard' }],
  '/app/cfo-dashboard':      [{ label: 'Workspace', to: '/app' }, { label: 'Dashboards' }, { label: 'CFO Dashboard' }],
  '/app/coo-dashboard':      [{ label: 'Workspace', to: '/app' }, { label: 'COO Dashboard' }],
  '/app/hr-dashboard':       [{ label: 'Workspace', to: '/app' }, { label: 'HR Dashboard' }],
  '/app/manager-dashboard':  [{ label: 'Workspace', to: '/app' }, { label: 'Manager Dashboard' }],
  '/app/employee-dashboard': [{ label: 'Workspace', to: '/app' }, { label: 'Employee Workspace' }],
  '/app/monitoring':         [{ label: 'Workspace', to: '/app' }, { label: 'Employee Monitoring' }],
  '/app/hr':                 [{ label: 'Workspace', to: '/app' }, { label: 'HR Management' }],
  '/app/projects':           [{ label: 'Workspace', to: '/app' }, { label: 'Projects & Tasks' }],
  '/app/crm':                [{ label: 'Workspace', to: '/app' }, { label: 'CRM & Pipeline' }],
  '/app/lead-hunter':        [{ label: 'Workspace', to: '/app' }, { label: 'Lead Hunter' }],
  '/app/automations':        [{ label: 'Workspace', to: '/app' }, { label: 'Automations' }],
  '/app/reports':            [{ label: 'Workspace', to: '/app' }, { label: 'Reports & Analytics' }],
  '/app/users':              [{ label: 'Administration' }, { label: 'Team & Roles' }],
  '/app/integrations':       [{ label: 'Administration' }, { label: 'Integrations & APIs' }],
  '/app/settings':           [{ label: 'Administration' }, { label: 'Settings' }],
  // CTO modules
  '/app/system-health':      [{ label: 'Workspace', to: '/app' }, { label: 'System Health' }],
  '/app/deployments':        [{ label: 'Workspace', to: '/app' }, { label: 'Deployments' }],
  '/app/incidents':          [{ label: 'Workspace', to: '/app' }, { label: 'Incidents & Alerts' }],
  '/app/documentation':      [{ label: 'Workspace', to: '/app' }, { label: 'Documentation' }],
  // CFO modules
  '/app/financial-overview': [{ label: 'Workspace', to: '/app' }, { label: 'Financial Overview' }],
  '/app/revenue-expenses':   [{ label: 'Workspace', to: '/app' }, { label: 'Revenue & Expenses' }],
  '/app/budgets':            [{ label: 'Workspace', to: '/app' }, { label: 'Budgets' }],
  '/app/payroll-summary':    [{ label: 'Workspace', to: '/app' }, { label: 'Payroll Summary' }],
  '/app/invoices':           [{ label: 'Workspace', to: '/app' }, { label: 'Invoices & Payments' }],
  '/app/forecasting':        [{ label: 'Workspace', to: '/app' }, { label: 'Forecasting' }],
  '/app/financial-reports':  [{ label: 'Workspace', to: '/app' }, { label: 'Financial Reports' }],
  '/app/departments':        [{ label: 'Workspace', to: '/app' }, { label: 'Departments' }],
};

export function crumbsFor(pathname: string): Crumb[] {
  if (TITLES[pathname]) return TITLES[pathname];
  return [{ label: 'Workspace', to: '/app' }];
}

const SUBTITLES: Record<string, string> = {
  '/app/dashboard':          'Your company at a glance',
  '/app/cto-dashboard':      'Engineering performance, platform reliability, and delivery at a glance',
  '/app/cfo-dashboard':      'Track financial performance, cash flow, budgets, and upcoming obligations',
  '/app/coo-dashboard':      'Operations, workforce presence and delivery',
  '/app/hr-dashboard':       'People, attendance, leave and HR management',
  '/app/manager-dashboard':  'Team tasks, leave approvals and pipeline deals',
  '/app/employee-dashboard': 'Personal work session, tasks and transparency log',
  '/app/monitoring':         'Live presence across your company',
  '/app/hr':                 'People, attendance and leave',
  '/app/projects':           'Delivery across every project',
  '/app/crm':                'Pipeline and client lifecycle',
  '/app/lead-hunter':        'Find your next customers',
  '/app/automations':        'Rules that run themselves',
  '/app/reports':            'Numbers leadership can trust',
  '/app/users':              'Roles and team access',
  '/app/integrations':       'Connected tools and API configurations',
  '/app/settings':           'Company preferences',
  '/app/system-health':      'Platform service uptime, latency and operational status',
  '/app/deployments':        'Release pipeline, deployment history and CI/CD activity',
  '/app/incidents':          'Open incidents, escalations and resolution tracking',
  '/app/documentation':      'Engineering runbooks, API references and onboarding guides',
  '/app/financial-overview': 'High-level financial health snapshot across the company',
  '/app/revenue-expenses':   'Detailed revenue and cost breakdown by period',
  '/app/budgets':            'Departmental budget allocations and utilisation tracking',
  '/app/payroll-summary':    'Payroll cycles, headcount costs and upcoming obligations',
  '/app/invoices':           'Outstanding invoices, payment status and collections',
  '/app/forecasting':        'Revenue and expense projections for future periods',
  '/app/financial-reports':  'Exportable P&L, balance sheets and audit-ready summaries',
  '/app/departments':        'Department-level cost centres, headcount and budgets',
};

export function subtitleFor(pathname: string): string {
  return SUBTITLES[pathname] ?? '';
}

/** Keeps the browser tab title in sync with the current section. */
export function useDocumentTitle(pathname: string) {
  useEffect(() => {
    const crumbs = crumbsFor(pathname);
    document.title = `${crumbs[crumbs.length - 1].label} | EMS`;
  }, [pathname]);
}
