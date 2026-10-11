import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { ToastProvider } from '@/components/ui/Toast';
import { CeoDashboardPage } from '@/pages/CeoDashboardPage';
import { CfoDashboardPage } from '@/pages/CfoDashboardPage';
import { CompanySetupPage } from '@/pages/CompanySetupPage';
import { CooDashboardPage } from '@/pages/CooDashboardPage';
import { CtoDashboardPage } from '@/pages/CtoDashboardPage';
import { EmployeeDashboardPage } from '@/pages/EmployeeDashboardPage';
import { ForgotPasswordPage } from '@/pages/ForgotPasswordPage';
import { HrDashboardPage } from '@/pages/HrDashboardPage';
import { InviteTeamPage } from '@/pages/InviteTeamPage';
import { LoginPage } from '@/pages/LoginPage';
import { ManagerDashboardPage } from '@/pages/ManagerDashboardPage';
import {
  AutomationsPage,
  BudgetsPage,
  CrmPage,
  DepartmentsPage,
  DeploymentsPage,
  DocumentationPage,
  FinancialOverviewPage,
  FinancialReportsPage,
  ForecastingPage,
  HrPage,
  IncidentsPage,
  IntegrationsPage,
  InvoicesPage,
  LeadHunterPage,
  MonitoringPage,
  PayrollSummaryPage,
  ProjectsPage,
  ReportsPage,
  RevenueExpensesPage,
  SettingsPage,
  SystemHealthPage,
  UsersPage,
} from '@/pages/ModulePages';
import { NotFoundPage } from '@/pages/NotFoundPage';
import { RegisterPage } from '@/pages/RegisterPage';
import { ResetPasswordPage } from '@/pages/ResetPasswordPage';
import { Role } from '@/lib/enums';
import { AppRoutes, RequireAuth, RequireRole, RoleHomeRedirect } from '@/routes/guards';

const queryClient = new QueryClient();

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
            <Route path="/forgot-password" element={<ForgotPasswordPage />} />
            <Route path="/reset-password" element={<ResetPasswordPage />} />
            <Route path="/company-setup" element={<CompanySetupPage />} />
            <Route path="/invite-team" element={<InviteTeamPage />} />

            {/* All /app/* routes require authentication */}
            <Route element={<RequireAuth />}>
              <Route element={<AppRoutes />}>
                {/* Generic /app redirect → role home */}
                <Route path="/app" element={<RoleHomeRedirect />} />

                {/* ── Role-gated dashboards ──────────────────────────────── */}
                <Route
                  path="/app/dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Ceo]}>
                      <CeoDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/cto-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Cto]}>
                      <CtoDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/cfo-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Cfo]}>
                      <CfoDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/coo-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Coo]}>
                      <CooDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/hr-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Hr]}>
                      <HrDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/manager-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Manager]}>
                      <ManagerDashboardPage />
                    </RequireRole>
                  }
                />
                <Route
                  path="/app/employee-dashboard"
                  element={
                    <RequireRole allowedRoles={[Role.Employee]}>
                      <EmployeeDashboardPage />
                    </RequireRole>
                  }
                />

                {/* ── Shared / multi-role module routes ─────────────────── */}
                <Route path="/app/monitoring" element={<MonitoringPage />} />
                <Route path="/app/hr" element={<HrPage />} />
                <Route path="/app/projects" element={<ProjectsPage />} />
                <Route path="/app/crm" element={<CrmPage />} />
                <Route path="/app/lead-hunter" element={<LeadHunterPage />} />
                <Route path="/app/automations" element={<AutomationsPage />} />
                <Route path="/app/reports" element={<ReportsPage />} />
                <Route path="/app/users" element={<UsersPage />} />
                <Route path="/app/integrations" element={<IntegrationsPage />} />
                <Route path="/app/settings" element={<SettingsPage />} />

                {/* ── CTO-specific module routes ─────────────────────────── */}
                <Route path="/app/system-health" element={<SystemHealthPage />} />
                <Route path="/app/deployments" element={<DeploymentsPage />} />
                <Route path="/app/incidents" element={<IncidentsPage />} />
                <Route path="/app/documentation" element={<DocumentationPage />} />

                {/* ── CFO-specific module routes ─────────────────────────── */}
                <Route path="/app/financial-overview" element={<FinancialOverviewPage />} />
                <Route path="/app/revenue-expenses" element={<RevenueExpensesPage />} />
                <Route path="/app/budgets" element={<BudgetsPage />} />
                <Route path="/app/payroll-summary" element={<PayrollSummaryPage />} />
                <Route path="/app/invoices" element={<InvoicesPage />} />
                <Route path="/app/forecasting" element={<ForecastingPage />} />
                <Route path="/app/financial-reports" element={<FinancialReportsPage />} />
                <Route path="/app/departments" element={<DepartmentsPage />} />
              </Route>
            </Route>

            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
}
