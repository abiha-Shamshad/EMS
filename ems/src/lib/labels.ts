// UI labels for shared enum values. Screens never hard-code these labels.
import { Role, type InvitableRole } from './enums';

export const ROLE_LABELS: Record<Role, string> = {
  [Role.Ceo]: 'CEO',
  [Role.Cto]: 'CTO',
  [Role.Cfo]: 'CFO',
  [Role.Coo]: 'COO',
  [Role.Hr]: 'HR',
  [Role.Manager]: 'Manager',
  [Role.Employee]: 'Employee',
};

export const INVITE_ROLE_OPTIONS: ReadonlyArray<{ value: InvitableRole; label: string }> = [
  { value: Role.Employee, label: 'Employee' },
  { value: Role.Hr, label: 'HR' },
  { value: Role.Manager, label: 'Manager' },
];

export function roleLabel(role: Role): string {
  return ROLE_LABELS[role] ?? role;
}
