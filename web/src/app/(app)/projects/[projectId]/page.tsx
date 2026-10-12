"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Async, Field, FormError, Modal, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, patch, post } from "@/lib/api";
import { dateTime, label, minutes } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Status = "todo" | "active" | "review" | "done";
type Task = { id: string; title: string; assignee_id: string | null; assignee: string | null; due_at: string | null; position: number; version: number;
  billable: boolean; estimate_minutes: number | null; minutes_logged: number };
type Board = { project: { id: string; name: string; client: string | null; status: string; billing_type: string }; columns: Record<Status, Task[]>;
  column_truncated: Record<Status, boolean> };

const COLS: Status[] = ["todo", "active", "review", "done"];
const NAMES: Record<Status, string> = { todo: "To do", active: "Active", review: "Review", done: "Done" };
// Board moves allowed by the API (Section 12): todo<->active, active<->review, review->done, done->review.
const MOVES: Record<Status, Status[]> = { todo: ["active"], active: ["todo", "review"], review: ["active", "done"], done: ["review"] };

const toLocalInput = (iso: string | null) => (iso ? new Date(new Date(iso).getTime() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 16) : "");
const fromLocalInput = (v: string) => (v ? new Date(v).toISOString() : null);

/** Screen 34 - project details and Kanban (API-040, API-043), with screen 35 task create/edit/details and time logging (API-041/042/044). */
export default function ProjectBoardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const toast = useToast();
  const { me, timeZone } = useSession();
  const [assignee, setAssignee] = useState("");
  const board = useApi<Board>(`/projects/${projectId}/board`, { assignee_id: assignee || null });
  const members = useApi<Page<Member>>("/members", { limit: 100, status: "active" });
  const [drag, setDrag] = useState<{ task: Task; from: Status } | null>(null);
  const [over, setOver] = useState<Status | null>(null);
  const [editing, setEditing] = useState<{ task: Task | null; status: Status } | null>(null);
  const [now] = useState(() => Date.now());             // "overdue" is judged against page load time

  async function move(task: Task, from: Status, to: Status) {
    if (from === to) return;
    if (!MOVES[from].includes(to)) {
      toast(`${NAMES[from]} → ${NAMES[to]} is not allowed. Allowed: ${MOVES[from].map((s) => NAMES[s]).join(", ")}.`, "error");
      return;
    }
    try {
      await post(`/tasks/${task.id}/move`, { expected_version: task.version, to_status: to, position: (board.data?.columns[to].length ?? 0) + 1 });
    } catch (e) {
      toast((e as ApiError).code === "VERSION_CONFLICT" ? "Someone changed this task. The board was reloaded." : (e as ApiError).message, "error");
    }
    board.reload();
  }

  return (
    <Async state={board}>
      {(b) => (
        <>
          <PageHeader title={b.project.name} subtitle={<><Link href="/projects">Projects</Link> · {b.project.client ?? "Internal"} · {label(b.project.billing_type)} · <StatusBadge value={b.project.status} /></>}
            actions={<>
              <select className="select" style={{ width: 190 }} value={assignee} onChange={(e) => setAssignee(e.target.value)} aria-label="Assignee">
                <option value="">Everyone</option>{(members.data?.items ?? []).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>
              <button className="btn" onClick={() => setEditing({ task: null, status: "todo" })}>New task</button>
            </>} />
          <p className="muted small">Drag cards between columns. Allowed moves: To do ↔ Active ↔ Review → Done (and back to Review).</p>
          <div className="board">
            {COLS.map((s) => (
              <div key={s} className={`column ${over === s ? "drop" : ""}`}
                onDragOver={(e) => { if (drag && MOVES[drag.from].includes(s)) { e.preventDefault(); setOver(s); } }}
                onDragLeave={() => setOver(null)}
                onDrop={(e) => { e.preventDefault(); setOver(null); if (drag) void move(drag.task, drag.from, s); setDrag(null); }}>
                <div className="column-head"><span>{NAMES[s]}</span><span className="badge">{b.columns[s].length}{b.column_truncated[s] ? "+" : ""}</span></div>
                {b.columns[s].map((t) => {
                  const overdue = t.due_at && s !== "done" && new Date(t.due_at).getTime() < now;
                  return (
                    <div key={t.id} className="kcard" draggable onDragStart={() => setDrag({ task: t, from: s })} onDragEnd={() => setDrag(null)}
                      onClick={() => setEditing({ task: t, status: s })} role="button" tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setEditing({ task: t, status: s })}>
                      <h4>{t.title}</h4>
                      <div className="row between small"><span className="muted">{t.assignee ?? "Unassigned"}</span>
                        {t.due_at && <span className={overdue ? "badge danger" : "muted"}>{overdue ? "Overdue" : `Due ${dateTime(t.due_at, timeZone)}`}</span>}</div>
                      <div className="row gap-sm small muted">{minutes(t.minutes_logged)} logged{t.estimate_minutes ? ` of ${minutes(t.estimate_minutes)}` : ""}
                        {!t.billable && <span className="badge">non-billable</span>}</div>
                      <div className="row gap-sm wrap">
                        {MOVES[s].map((to) => <button key={to} className="btn sm ghost" onClick={(e) => { e.stopPropagation(); void move(t, s, to); }}>→ {NAMES[to]}</button>)}
                      </div>
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
          {editing && (
            <TaskEditor projectId={projectId} task={editing.task} members={members.data?.items ?? []} meId={me.user.id}
              onClose={() => setEditing(null)} onSaved={() => { setEditing(null); board.reload(); }} />
          )}
        </>
      )}
    </Async>
  );
}

function TaskEditor({ projectId, task, members, meId, onClose, onSaved }: {
  projectId: string; task: Task | null; members: Member[]; meId: string; onClose: () => void; onSaved: () => void;
}) {
  const toast = useToast();
  const [f, setF] = useState({ title: task?.title ?? "", assignee_id: task?.assignee_id ?? "", due_at: toLocalInput(task?.due_at ?? null),
    estimate: task?.estimate_minutes ? String(task.estimate_minutes / 60) : "", billable: task?.billable ?? true });
  const [log, setLog] = useState(() => ({ started_at: toLocalInput(new Date(Date.now() - 3600_000).toISOString()), minutes: "60", note: "" }));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body = { title: f.title, assignee_id: f.assignee_id || null, due_at: fromLocalInput(f.due_at),
      estimate_minutes: f.estimate ? Math.round(Number(f.estimate) * 60) : null, billable: f.billable };
    try {
      if (task) await patch(`/tasks/${task.id}`, { expected_version: task.version, ...body });
      else await post(`/projects/${projectId}/tasks`, body, { idempotencyKey: key });
      toast(task ? "Task saved" : "Task created");
      onSaved();
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  async function logTime() {
    if (!task) return;
    setBusy(true);
    setError(null);
    try {
      await post(`/tasks/${task.id}/time-entries`, { started_at: fromLocalInput(log.started_at), minutes: Number(log.minutes), ...(log.note ? { note: log.note } : {}) },
        { idempotent: true });
      toast(`${log.minutes} min logged`);
      onSaved();
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  return (
    <Modal wide title={task ? "Task details" : "New task"} subtitle={task ? `${minutes(task.minutes_logged)} logged so far` : undefined} onClose={onClose} footer={<>
      <button className="btn ghost" onClick={onClose}>Close</button>
      <button className="btn" form="task-form" disabled={busy || !f.title}>{busy ? "Saving…" : task ? "Save changes" : "Create task"}</button></>}>
      <form id="task-form" className="form-grid" onSubmit={save} noValidate>
        <Field label="Title" error={fe.title} className="full">
          {(id, inv) => <input id={id} className="input" maxLength={200} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} aria-invalid={inv} autoFocus />}
        </Field>
        <Field label="Assignee" error={fe.assignee_id}>
          {(id) => <select id={id} className="select" value={f.assignee_id} onChange={(e) => setF({ ...f, assignee_id: e.target.value })}>
            <option value="">Unassigned</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}{m.user_id === meId ? " (me)" : ""}</option>)}</select>}
        </Field>
        <Field label="Due" error={fe.due_at}>
          {(id, inv) => <input id={id} className="input" type="datetime-local" value={f.due_at} onChange={(e) => setF({ ...f, due_at: e.target.value })} aria-invalid={inv} />}
        </Field>
        <Field label="Estimate (hours)" error={fe.estimate_minutes}>
          {(id, inv) => <input id={id} className="input" type="number" min={0} step={0.25} value={f.estimate} onChange={(e) => setF({ ...f, estimate: e.target.value })} aria-invalid={inv} />}
        </Field>
        <label className="check" style={{ alignSelf: "end", paddingBottom: 10 }}>
          <input type="checkbox" checked={f.billable} onChange={(e) => setF({ ...f, billable: e.target.checked })} /> Billable to the client
        </label>
      </form>
      {task && (
        <div className="card" style={{ background: "var(--surface-2)" }}>
          <h3 className="h3" style={{ marginBottom: 10 }}>Log time manually</h3>
          <p className="muted small" style={{ marginBottom: 10 }}>For meetings or offline work. Time in the Employee Room is logged automatically at check-out; overlapping entries are refused.</p>
          <div className="form-grid">
            <Field label="Started" error={fe.started_at}>
              {(id, inv) => <input id={id} className="input" type="datetime-local" value={log.started_at} onChange={(e) => setLog({ ...log, started_at: e.target.value })} aria-invalid={inv} />}
            </Field>
            <Field label="Minutes" error={fe.minutes}>
              {(id, inv) => <input id={id} className="input" type="number" min={1} max={1440} value={log.minutes} onChange={(e) => setLog({ ...log, minutes: e.target.value })} aria-invalid={inv} />}
            </Field>
            <Field label="Note (optional)" className="full">
              {(id) => <input id={id} className="input" maxLength={2000} value={log.note} onChange={(e) => setLog({ ...log, note: e.target.value })} />}
            </Field>
          </div>
          <div className="row end" style={{ marginTop: 10 }}><button className="btn ghost" disabled={busy} onClick={() => void logTime()}>Log time</button></div>
        </div>
      )}
      <FormError error={error && !Object.keys(fe).length ? error : null} />
    </Modal>
  );
}
