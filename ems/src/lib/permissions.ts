// Role-based UI gating. Screens use ONLY this helper to decide visibility.
// Hiding UI is not security: the backend still enforces every permission.
import { Role } from './enums';

export const PERMISSIONS = {
  roomSelf: 'room.self',
  roomViewLive: 'room.view_live',
  hrManage: 'hr.manage',
  leaveDecide: 'leave.decide',
  membersManage: 'members.manage',
  projectsManage: 'projects.manage',
  crmManage: 'crm.manage',
  financeManage: 'finance.manage',
  hunterUse: 'hunter.use',
  rulesManage: 'rules.manage',
  leakageRead: 'leakage.read',
  leakageResolve: 'leakage.resolve',
  dashboardsAll: 'dashboards.all',
} as const;
export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

// Mirrors the Release 1 permission matrix (Implementation Spec, section 7.2).
const ROLE_PERMISSIONS: Record<Role, ReadonlyArray<Permission>> = {
  [Role.Ceo]: Object.values(PERMISSIONS),
  [Role.Cto]: [PERMISSIONS.roomSelf, PERMISSIONS.projectsManage, PERMISSIONS.rulesManage],
  [Role.Cfo]: [PERMISSIONS.roomSelf, PERMISSIONS.financeManage, PERMISSIONS.leakageRead],
  [Role.Coo]: [
    PERMISSIONS.roomSelf,
    PERMISSIONS.roomViewLive,
    PERMISSIONS.hrManage,
    PERMISSIONS.projectsManage,
    PERMISSIONS.crmManage,
    PERMISSIONS.hunterUse,
    PERMISSIONS.rulesManage,
    PERMISSIONS.leakageRead,
  ],
  [Role.Hr]: [
    PERMISSIONS.roomSelf,
    PERMISSIONS.hrManage,
    PERMISSIONS.leaveDecide,
    PERMISSIONS.membersManage,
  ],
  [Role.Manager]: [
    PERMISSIONS.roomSelf,
    PERMISSIONS.leaveDecide,
    PERMISSIONS.projectsManage,
    PERMISSIONS.crmManage,
    PERMISSIONS.hunterUse,
  ],
  [Role.Employee]: [PERMISSIONS.roomSelf],
};

export function can(role: Role | null | undefined, permission: Permission): boolean {
  if (!role) return false;
  return ROLE_PERMISSIONS[role]?.includes(permission) ?? false;
}

export function dashboardPathForRole(role: Role | null | undefined): string {
  switch (role) {
    case Role.Cto:
      return '/app/cto-dashboard';
    case Role.Cfo:
      return '/app/cfo-dashboard';
    case Role.Coo:
      return '/app/coo-dashboard';
    case Role.Hr:
      return '/app/hr-dashboard';
    case Role.Manager:
      return '/app/manager-dashboard';
    case Role.Employee:
      return '/app/employee-dashboard';
    case Role.Ceo:
    default:
      return '/app/dashboard';
  }
}

