// Shapes of the API responses the shell and several screens share (contracts/api-examples.json).

export type Role = "ceo" | "cto" | "cfo" | "coo" | "hr" | "manager" | "employee";

export type Permission =
  | "room.view_live" | "room.self" | "hr.manage" | "leave.decide" | "projects.manage" | "crm.manage" | "finance.manage"
  | "hunter.use" | "rules.manage" | "members.manage" | "leakage.read" | "leakage.resolve" | "dashboards.all";

export type Me = {
  user: { id: string; name: string; email: string };
  active_org: { id: string; name: string; role: Role; time_zone: string; setup_state: string };
  permissions: Permission[];
  dashboard: "ceo" | "cto" | "cfo" | "coo" | "hr" | "employee";
};

export type Page<T> = { items: T[]; next_cursor: string | null };

export type Member = {
  user_id: string; name: string; role: Role; title: string | null; department: string | null; status: "active" | "deactivated";
  version: number; manager_id?: string; cost_rate?: string | null;
};

export type Tile = { key: string; label: string; value: unknown; source: string; [extra: string]: unknown };
export type Gap = { key: string; reason: string };

/** A live view opened from the grid (API-026), kept in sessionStorage for the viewer page. */
export type OpenView = { view_id: string; livekit_url: string; token: string; room: string; expires_in_seconds: number; subject: string };

export type LeaveRow = { request_id: string; employee: string; kind: string; start_date: string; end_date: string; days: number; status: string;
  team_on_leave_same_days: number; version: number };

export type ContactRow = { id: string; name: string; company: string | null; lifecycle_stage: string; owner: string | null; last_activity_at: string | null };

/** The CEO video wall (POST /room/stream/view-grid): one logged view and token per live employee. */
export type GridView = { livekit_url: string; expires_in_seconds: number; opened_at: number;
  items: { view_id: string; token: string; room: string; subject_user_id: string; name: string; camera: boolean; screen: boolean }[] };
