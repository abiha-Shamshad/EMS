"use client";

import { useState, type FormEvent } from "react";

import { InviteForm } from "@/components/forms/InviteForm";
import { Async, Avatar, Card, ConfirmDialog, Empty, Field, FormError, Modal, NoAccess, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, patch, post } from "@/lib/api";
import { label, money } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

const ROLES = ["ceo", "cto", "cfo", "coo", "hr", "manager", "employee"];

/** Screen 47 - user and role management (API-013/014/015) and invitations (API-011). */
export default function MembersPage() {
  const toast = useToast();
  const { me, can } = useSession();
  const [status, setStatus] = useState<"active" | "deactivated">("active");
  const list = useApi<Page<Member>>("/members", { status, limit: 100 });
  const all = useApi<Page<Member>>("/members", { status: "active", limit: 100 });
  const [editing, setEditing] = useState<Member | null>(null);
  const [removing, setRemoving] = useState<Member | null>(null);
  const [inviting, setInviting] = useState(false);
  if (!can("members.manage") && !can("finance.manage")) return <NoAccess message="Only the CEO and HR manage people; the CFO sets cost rates." />;

  return (
    <>
      <PageHeader title="Users & roles" subtitle="Seven fixed roles. Only the CEO gives CTO, CFO or COO, and nobody changes their own role."
        actions={<>
          <select className="select" style={{ width: 150 }} value={status} onChange={(e) => setStatus(e.target.value as typeof status)} aria-label="Status">
            <option value="active">Active</option><option value="deactivated">Deactivated</option></select>
          {can("members.manage") && <button className="btn" onClick={() => setInviting(true)}>Invite people</button>}
        </>} />
      <Card flush>
        <Async state={list}>
          {(l) => l.items.length === 0 ? <Empty title="No one here" /> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Name</th><th>Role</th><th>Title</th><th>Department</th>{can("finance.manage") && <th className="num">Cost rate / h</th>}<th>Status</th><th /></tr></thead>
              <tbody>{l.items.map((m) => (
                <tr key={m.user_id}>
                  <td><div className="row gap"><Avatar name={m.name} /><b>{m.name}</b>{m.user_id === me.user.id && <span className="badge">You</span>}</div></td>
                  <td>{label(m.role)}</td><td>{m.title ?? "—"}</td><td>{m.department ?? "—"}</td>
                  {can("finance.manage") && <td className="num">{m.cost_rate ? money(m.cost_rate) : "—"}</td>}
                  <td><StatusBadge value={m.status} /></td>
                  <td className="num">{m.status === "active" && (
                    <div className="row gap-sm end">
                      <button className="btn sm ghost" onClick={() => setEditing(m)}>Edit</button>
                      {can("members.manage") && m.role !== "ceo" && m.user_id !== me.user.id && <button className="btn sm ghost" onClick={() => setRemoving(m)}>Deactivate</button>}
                    </div>
                  )}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </Async>
      </Card>
      {inviting && (
        <Modal wide title="Invite people" onClose={() => { setInviting(false); list.reload(); }}>
          <InviteForm isCeo={me.active_org.role === "ceo"} />
        </Modal>
      )}
      {editing && <EditMember member={editing} members={all.data?.items ?? []} isCeo={me.active_org.role === "ceo"} self={editing.user_id === me.user.id}
        canPeople={can("members.manage")} canCost={can("finance.manage")}
        onClose={() => setEditing(null)} onSaved={() => { setEditing(null); toast("Member updated"); list.reload(); all.reload(); }} />}
      {removing && <Deactivate member={removing} members={all.data?.items ?? []} onClose={() => setRemoving(null)}
        onDone={(r) => { setRemoving(null); toast(`${removing.name} deactivated · ${r.tasks_reassigned} tasks and ${r.deals_reassigned} deals reassigned`); list.reload(); all.reload(); }} />}
    </>
  );
}

function EditMember({ member, members, isCeo, self, canPeople, canCost, onClose, onSaved }: {
  member: Member; members: Member[]; isCeo: boolean; self: boolean; canPeople: boolean; canCost: boolean; onClose: () => void; onSaved: () => void;
}) {
  const [f, setF] = useState({ role: member.role, title: member.title ?? "", department: member.department ?? "", manager_id: member.manager_id ?? "",
    cost_rate: member.cost_rate ?? "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const fe = error?.fields ?? {};
  const roleOptions = ROLES.filter((r) => r === member.role || (r !== "ceo" && (isCeo || !["cto", "cfo", "coo"].includes(r))));

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = { expected_version: member.version };
    if (canPeople) {
      if (f.role !== member.role && !self) body.role = f.role;
      if (f.title !== (member.title ?? "")) body.title = f.title || null;
      if (f.department !== (member.department ?? "")) body.department = f.department || null;
      if (f.manager_id !== (member.manager_id ?? "")) body.manager_id = f.manager_id || null;
    }
    if (canCost && f.cost_rate !== (member.cost_rate ?? "") && f.cost_rate) body.cost_rate = f.cost_rate;
    if (Object.keys(body).length === 1) { onClose(); return; }
    try {
      await patch(`/members/${member.user_id}`, body);
      onSaved();
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }
  return (
    <Modal title={`Edit ${member.name}`} onClose={onClose} footer={<><button className="btn ghost" onClick={onClose}>Cancel</button>
      <button className="btn" form="member-form" disabled={busy}>{busy ? "Saving…" : "Save"}</button></>}>
      <form id="member-form" className="form-grid" onSubmit={submit} noValidate>
        {canPeople && <>
          <Field label="Role" error={fe.role} hint={self ? "You can't change your own role" : member.role === "ceo" ? "The CEO role is transferred separately" : undefined}>
            {(id, inv) => <select id={id} className="select" value={f.role} disabled={self || member.role === "ceo"} onChange={(e) => setF({ ...f, role: e.target.value as Member["role"] })} aria-invalid={inv}>
              {roleOptions.map((r) => <option key={r} value={r}>{label(r)}</option>)}</select>}</Field>
          <Field label="Manager" error={fe.manager_id}>
            {(id, inv) => <select id={id} className="select" value={f.manager_id} onChange={(e) => setF({ ...f, manager_id: e.target.value })} aria-invalid={inv}>
              <option value="">No manager</option>{members.filter((m) => m.user_id !== member.user_id).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>}</Field>
          <Field label="Title" error={fe.title}>{(id, inv) => <input id={id} className="input" maxLength={120} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} aria-invalid={inv} />}</Field>
          <Field label="Department" error={fe.department}>{(id, inv) => <input id={id} className="input" maxLength={120} value={f.department} onChange={(e) => setF({ ...f, department: e.target.value })} aria-invalid={inv} />}</Field>
        </>}
        {canCost && <Field label="Cost rate per hour" error={fe.cost_rate} hint="Internal cost for budgets and leakage, e.g. 12.50">
          {(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.cost_rate} onChange={(e) => setF({ ...f, cost_rate: e.target.value })} aria-invalid={inv} />}</Field>}
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}

function Deactivate({ member, members, onClose, onDone }: {
  member: Member; members: Member[]; onClose: () => void; onDone: (r: { tasks_reassigned: number; deals_reassigned: number }) => void;
}) {
  const [to, setTo] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  async function confirm() {
    setBusy(true);
    setError(null);
    try {
      onDone(await post(`/members/${member.user_id}/deactivate`, { reassign_to: to || null, reason: reason || null }, { idempotencyKey: key }));
    } catch (e) {
      setError(e as ApiError);
      setBusy(false);
    }
  }
  return (
    <ConfirmDialog title={`Deactivate ${member.name}?`} danger confirmLabel="Deactivate" busy={busy} error={error} onCancel={onClose} onConfirm={() => void confirm()}
      message="They lose access at once. Their open work session closes, live views end, and their open tasks, deals and projects move to the person you choose. History is kept.">
      <Field label="Reassign their work to" error={error?.fields.reassign_to}>
        {(id, inv) => <select id={id} className="select" value={to} onChange={(e) => setTo(e.target.value)} aria-invalid={inv}>
          <option value="">Nobody (only if they own no open deals or projects)</option>
          {members.filter((m) => m.user_id !== member.user_id).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>}</Field>
      <Field label="Reason (optional)">{(id) => <input id={id} className="input" maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} />}</Field>
    </ConfirmDialog>
  );
}
