"use client";

import { useState } from "react";

import { Async, Card, ConfirmDialog, Empty, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { dateTime, label, minutes, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Day = { date: string; status: string; check_in?: string; check_out?: string | null; minutes_late?: number; active?: number; idle?: number;
  locked?: number; on_break?: number; offline?: number };
type Attendance = { days: Day[] };
type Viewers = { items: { view_id: string; viewer: string; reason: string; started_at: string; seconds: number | null }[] };
type Breaks = { items: { id: string; kind: string; status: string; requested_minutes: number; minutes: number | null; created_at: string }[] };
type Org = { room_policy_version: number; live_view_enabled: boolean };

type Project = { id: string; name: string; status: string };
type Board = { columns: Record<string, { id: string; title: string }[]> };

/** The tasks assigned to me in my open projects, for the check-in task picker. */
function useMyTasks(meId: string) {
  const projects = useApi<Page<Project>>("/projects", { limit: 20 });
  const open = (projects.data?.items ?? []).filter((p) => !["completed", "cancelled"].includes(p.status)).slice(0, 5);
  const boards = [useApi<Board>(open[0] ? `/projects/${open[0].id}/board` : null, { assignee_id: meId }),
    useApi<Board>(open[1] ? `/projects/${open[1].id}/board` : null, { assignee_id: meId }),
    useApi<Board>(open[2] ? `/projects/${open[2].id}/board` : null, { assignee_id: meId }),
    useApi<Board>(open[3] ? `/projects/${open[3].id}/board` : null, { assignee_id: meId }),
    useApi<Board>(open[4] ? `/projects/${open[4].id}/board` : null, { assignee_id: meId })];
  return boards.flatMap((b, i) => (b.data && open[i] ? ["active", "todo", "review"].flatMap((c) => (b.data!.columns[c] ?? [])
    .map((t) => ({ id: t.id, title: `${t.title} · ${open[i]!.name}` }))) : []));
}

/** My workday: check in and out, today's session, breaks, consent (screen and webcam) and every live view of me
 *  (API-017, 018, 020, 023, 028, 030). The extension reports presence and shares; checking in here records attendance. */
export default function MyWorkdayPage() {
  const toast = useToast();
  const { me, timeZone } = useSession();
  const tasks = useMyTasks(me.user.id);
  const [task, setTask] = useState("");
  const [webcam, setWebcam] = useState(false);
  const day = today(timeZone);
  const att = useApi<Attendance>("/attendance", { from: day, to: day });
  const viewers = useApi<Viewers>("/room/my-viewers");
  const breaks = useApi<Breaks>("/room/breaks", { from: day, to: day });
  const org = useApi<Org>("/org");
  const [confirm, setConfirm] = useState<null | "checkout" | "withdraw">(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function run(fn: () => Promise<unknown>, done: string) {
    setBusy(true);
    setError(null);
    try {
      await fn();
      toast(done);
      setConfirm(null);
      att.reload();
      breaks.reload();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  async function consent(accept: boolean) {
    if (!org.data) return;
    await run(() => post("/room/consent", { policy_version: org.data!.room_policy_version, accept, ...(accept ? { webcam } : {}) }),
      accept ? (webcam ? "Consent recorded, including the webcam" : "Consent recorded (screen only)") : "Consent withdrawn. Screen and webcam sharing stopped.");
  }

  const d = att.data?.days[0];
  const open = d?.status === "present" && !d.check_out;
  const activeBreak = breaks.data?.items.find((b) => b.status === "active");
  return (
    <>
      <PageHeader title="My workday" subtitle="Check in and out here or from the EMS Chrome extension. The extension reports your presence and shares your webcam and screen." />
      <div className="grid grid-2">
        <Card title="Today" actions={open && <button className="btn sm danger" onClick={() => setConfirm("checkout")}>Check out</button>}>
          {d && d.status !== "present" && d.status !== "on_leave" && (
            <div className="stack-sm" style={{ marginBottom: 14 }}>
              <div className="row gap">
                <select className="select grow" value={task} onChange={(e) => setTask(e.target.value)} aria-label="Task">
                  <option value="">No task selected</option>{tasks.map((t) => <option key={t.id} value={t.id}>{t.title}</option>)}</select>
                <button className="btn" disabled={busy} onClick={() => void run(() => post("/room/check-in", { device: { kind: "web" }, task_id: task || null }), "Checked in")}>Check in</button>
              </div>
              <p className="muted small">Open the EMS extension afterwards and press Check in there too: it attaches to this session to report presence and share.</p>
            </div>
          )}
          <Async state={att}>
            {() => !d ? <Empty title="No working day today" /> : d.status !== "present" ? (
              <div className="stack-sm">
                <StatusBadge value={d.status} />
                <p className="muted">{d.status === "not_checked_in" ? "Check in above, or from the EMS extension, to start your day." : "Nothing recorded for today."}</p>
              </div>
            ) : (
              <dl className="kv">
                <dt>Status</dt><dd><StatusBadge value={open ? "checked_in" : "completed"} text={open ? "Checked in" : "Checked out"} /></dd>
                <dt>Check-in</dt><dd>{d.check_in}{d.minutes_late ? <span className="badge warning" style={{ marginLeft: 8 }}>{d.minutes_late} min late</span> : null}</dd>
                <dt>Check-out</dt><dd>{d.check_out ?? "—"}</dd>
                <dt>Active</dt><dd>{minutes(d.active)}</dd>
                <dt>Idle / locked</dt><dd>{minutes((d.idle ?? 0) + (d.locked ?? 0))}</dd>
                <dt>Breaks</dt><dd>{minutes(d.on_break)}</dd>
                <dt>Offline</dt><dd>{minutes(d.offline)}</dd>
              </dl>
            )}
          </Async>
        </Card>
        <Card title="Breaks today" actions={activeBreak && <button className="btn sm" onClick={() => void run(() => post(`/room/breaks/${activeBreak.id}/end`), "Break ended")}>End break</button>}>
          <Async state={breaks}>
            {(b) => b.items.length === 0 ? <p className="muted">No breaks today. Request one from the extension&apos;s break panel.</p> : (
              <div className="list">{b.items.map((x) => (
                <div key={x.id} className="list-item"><StatusBadge value={x.status} /><span className="grow">{label(x.kind)} · {x.requested_minutes} min requested</span>
                  <span className="muted small">{x.minutes !== null ? minutes(x.minutes) : ""}</span></div>
              ))}</div>
            )}
          </Async>
        </Card>
        <Card title="Monitoring consent" subtitle="Covers presence, idle state, current task and live screen while checked in, and your webcam if you opt in. Never recording, keystrokes, browsing history or microphone.">
          <div className="stack-sm">
            <p className="muted">{org.data?.live_view_enabled ? "Live viewing is on for your company." : "Live viewing is currently switched off for your company."} Notice version {org.data?.room_policy_version ?? "…"}.</p>
            <label className="check"><input type="checkbox" checked={webcam} onChange={(e) => setWebcam(e.target.checked)} />
              Also share my webcam live while I am checked in (paused on breaks, never recorded)</label>
            <div className="row gap">
              <button className="btn" disabled={busy || !org.data} onClick={() => void consent(true)}>I consent</button>
              <button className="btn ghost" disabled={busy || !org.data} onClick={() => setConfirm("withdraw")}>Withdraw consent</button>
            </div>
            {error && !confirm && <div className="alert error">{error.message}</div>}
          </div>
        </Card>
        <Card title="Who viewed me live" subtitle="Every live view of your webcam or screen, with the reason. No role can hide this.">
          <Async state={viewers}>
            {(v) => v.items.length === 0 ? <p className="muted">Nobody has viewed you live in the last 7 days.</p> : (
              <div className="list">{v.items.map((x) => (
                <div key={x.view_id} className="list-item">
                  <div className="grow"><b>{x.viewer}</b> <span className="muted">· {x.reason}</span>
                    <div className="muted small">{dateTime(x.started_at, timeZone)} · {x.seconds === null ? "viewing now" : `${Math.max(1, Math.round(x.seconds / 60))} min`}</div></div>
                </div>
              ))}</div>
            )}
          </Async>
        </Card>
      </div>
      {confirm === "checkout" && (
        <ConfirmDialog title="Check out now?" message="This closes today's work session and turns your active task time into time entries." confirmLabel="Check out"
          busy={busy} error={error} onCancel={() => setConfirm(null)} onConfirm={() => void run(() => post("/room/check-out", {}), "Checked out. Good work today.")} />
      )}
      {confirm === "withdraw" && (
        <ConfirmDialog title="Withdraw consent?" danger confirmLabel="Withdraw" busy={busy} error={error} onCancel={() => setConfirm(null)} onConfirm={() => void consent(false)}
          message="Screen and webcam sharing stop at once and anyone viewing is disconnected. You can still check in for attendance." />
      )}
    </>
  );
}
