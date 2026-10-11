// Shared enums - the ONLY allowed values (Engineering Handbook, section 5).
// TODO(contract): replace with imports from shared/api-types.ts once `npm run gen:api` exists.
export const Role = {
  Ceo: 'ceo',
  Cto: 'cto',
  Cfo: 'cfo',
  Coo: 'coo',
  Hr: 'hr',
  Manager: 'manager',
  Employee: 'employee',
} as const;
export type Role = (typeof Role)[keyof typeof Role];

/** Roles that can be picked on the Invite screen (design shows Employee/HR/Manager). */
export const INVITABLE_ROLES = [Role.Employee, Role.Hr, Role.Manager] as const;
export type InvitableRole = (typeof INVITABLE_ROLES)[number];

export const Presence = {
  Online: 'online',
  Idle: 'idle',
  OnBreak: 'on_break',
  Offline: 'offline',
} as const;
export type Presence = (typeof Presence)[keyof typeof Presence];

export const LeaveStatus = {
  Pending: 'pending',
  ForwardedToCeo: 'forwarded_to_ceo',
  Approved: 'approved',
  Rejected: 'rejected',
  Canceled: 'canceled',
} as const;
export type LeaveStatus = (typeof LeaveStatus)[keyof typeof LeaveStatus];

export const LeaveType = {
  Casual: 'casual',
  Sick: 'sick',
  Annual: 'annual',
  Unpaid: 'unpaid',
} as const;
export type LeaveType = (typeof LeaveType)[keyof typeof LeaveType];
