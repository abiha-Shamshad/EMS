// Pure state rules shared by the service worker and the pages (unit-tested in test/logic.test.mjs).

export type Presence = "active" | "idle" | "locked" | "on_break" | "offline";
export type BreakState =
  | { status: "none" }
  | { status: "requested"; id: string; kind: string; minutes: number }
  | { status: "active"; id: string; kind: string; minutes: number; started_at: string };

export type WorkSession = { id: string; token: string; started_at: string; task_id: string | null; streaming_required: boolean;
  camera_allowed?: boolean };

export type HeartbeatResponse = { presence: Presence; server_time: string; next_heartbeat_seconds: number;
  pending_break_decision: { break_id: string; status: "requested" } | null };

/** Body of API-019. `streaming` / `camera` are only true while the Media Session Page is really publishing and no break runs. */
export function heartbeatBody(session: WorkSession, idle: "active" | "idle" | "locked", streaming: boolean, brk: BreakState, now: Date,
  camera = false) {
  const live = brk.status !== "active";
  return { session_id: session.id, sent_at: now.toISOString(), idle_state: idle, streaming: streaming && live, camera: camera && live };
}

/** A pending break request ends when the server stops reporting it: on_break means approved (now active), anything else rejected. */
export function breakAfterHeartbeat(brk: BreakState, res: HeartbeatResponse, now: Date): BreakState {
  if (brk.status !== "requested") return brk;
  if (res.pending_break_decision?.break_id === brk.id) return brk;
  if (res.presence === "on_break") return { status: "active", id: brk.id, kind: brk.kind, minutes: brk.minutes, started_at: now.toISOString() };
  return { status: "none" };
}

/** Views still open (seconds === null) from API-028: the employee is told who is watching right now (Section 9.5). */
export function openViewers(items: { viewer: string; reason: string; seconds: number | null }[]): { viewer: string; reason: string }[] {
  return items.filter((v) => v.seconds === null).map((v) => ({ viewer: v.viewer, reason: v.reason }));
}

/** Whether the monitoring notice must be shown (first sign-in, or HR published a new version - Section 9.2). */
export function needsConsent(consentedVersion: number | undefined, currentVersion: number): boolean {
  return consentedVersion === undefined || consentedVersion < currentVersion;
}

export function minutesSince(iso: string, now: Date): number {
  return Math.max(0, Math.floor((now.getTime() - new Date(iso).getTime()) / 60000));
}
