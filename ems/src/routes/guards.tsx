import { Navigate, Outlet } from 'react-router-dom';
import { AppShell } from '@/components/layout/AppShell';
import { Role } from '@/lib/enums';
import { dashboardPathForRole } from '@/lib/permissions';
import { getSession } from '@/lib/session';

/** Route guard: anything under /app needs a session (demo or real). */
export function RequireAuth() {
  if (!getSession()) return <Navigate to="/login" replace />;
  return <Outlet />;
}

export function AppRoutes() {
  return <AppShell />;
}

/** Resolves the authenticated user's home dashboard route according to their role. */
export function RoleHomeRedirect() {
  const session = getSession();
  const role = session?.user.role;
  const target = dashboardPathForRole(role);
  return <Navigate to={target} replace />;
}

/** Route guard for role-specific dashboard views. */
export function RequireRole({
  allowedRoles,
  children,
}: {
  allowedRoles: Role[];
  children: React.ReactNode;
}) {
  const session = getSession();
  const role = session?.user.role;
  if (!role || !allowedRoles.includes(role)) {
    // Redirect unauthorized attempt to their own dashboard
    return <Navigate to={dashboardPathForRole(role)} replace />;
  }
  return <>{children}</>;
}
