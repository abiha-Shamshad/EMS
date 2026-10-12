"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Async, ConfirmDialog, Field, FormError, Modal, NoAccess, PageHeader, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { label, money, relative, sumMoney } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Deal = { id: string; title: string; stage: string; amount: string; currency: string; expected_close: string | null; last_activity_at: string; version: number;
  owner: { id: string; name: string }; contact: { id: string; name: string }; company: string | null; stale: boolean };
const OPEN = ["new", "qualified", "proposal", "negotiation"] as const;

/** Screen 39 - sales pipeline board (deal cards, API-050 stage moves, API-051 Win, lost with a reason). */
export default function PipelinePage() {
  const router = useRouter();
  const toast = useToast();
  const { can, me } = useSession();
  const canRead = can("crm.manage") || me.active_org.role === "cfo";
  const deals = useApi<Page<Deal>>(canRead ? "/deals" : null, { limit: 100 });
  const [drag, setDrag] = useState<Deal | null>(null);
  const [lost, setLost] = useState<Deal | null>(null);
  const [reason, setReason] = useState("");
  const [winning, setWinning] = useState<Deal | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  if (!canRead) return <NoAccess message="Only sales leadership, managers and the CFO can open the pipeline." />;
  const edit = can("crm.manage");

  async function stage(d: Deal, to: string, lostReason?: string) {
    if (d.stage === to) return;
    setBusy(true);
    setError(null);
    try {
      await post(`/deals/${d.id}/stage`, { expected_version: d.version, to_stage: to, ...(lostReason ? { lost_reason: lostReason } : {}) });
      toast(`${d.title} moved to ${label(to)}`);
      setLost(null);
    } catch (e) {
      const err = e as ApiError;
      if (lost) setError(err);
      else toast(err.code === "VERSION_CONFLICT" ? "Someone changed this deal. The board was reloaded." : err.message, "error");
    } finally {
      setBusy(false);
      deals.reload();
    }
  }

  return (
    <Async state={deals}>
      {(p) => {
        const won = p.items.filter((d) => d.stage === "won").slice(0, 5);
        return (
          <>
            <PageHeader title="Sales pipeline" subtitle={edit ? "Drag deals between stages. Win starts the client and kickoff project in one step." : "Read-only for your role"}
              actions={<Link className="btn ghost" href="/crm/contacts">Add a deal from a contact</Link>} />
            <div className="board" style={{ ["--cols" as string]: 4 }}>
              {OPEN.map((s) => {
                const col = p.items.filter((d) => d.stage === s);
                return (
                  <div key={s} className="column" onDragOver={(e) => edit && drag && e.preventDefault()} onDrop={(e) => { e.preventDefault(); if (drag) void stage(drag, s); setDrag(null); }}>
                    <div className="column-head"><span>{label(s)}</span><span className="small">{money(sumMoney(col.map((d) => d.amount)), col[0]?.currency ?? "USD")}</span></div>
                    {col.map((d) => (
                      <div key={d.id} className="kcard" draggable={edit} onDragStart={() => setDrag(d)} onDragEnd={() => setDrag(null)}>
                        <h4><Link href={`/crm/contacts/${d.contact.id}`}>{d.title}</Link></h4>
                        <div className="row between small"><span className="muted">{d.company ?? d.contact.name}</span><b>{money(d.amount, d.currency)}</b></div>
                        <div className="row between small"><span className="muted">{d.owner.name}</span>
                          {d.stale ? <span className="badge danger">No activity {relative(d.last_activity_at)}</span> : <span className="muted">{relative(d.last_activity_at)}</span>}</div>
                        {edit && (
                          <div className="row gap-sm wrap">
                            <button className="btn sm" onClick={() => setWinning(d)}>Win</button>
                            <button className="btn sm ghost" onClick={() => { setLost(d); setReason(""); setError(null); }}>Lost</button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>
            {won.length > 0 && (
              <div className="card"><h3 className="h3" style={{ marginBottom: 8 }}>Recently won</h3>
                {won.map((d) => <div key={d.id} className="row between list-item"><span>{d.title} · {d.company ?? d.contact.name}</span><b>{money(d.amount, d.currency)}</b></div>)}</div>
            )}
            {lost && (
              <ConfirmDialog title={`Mark ${lost.title} as lost?`} message="Lost deals leave the pipeline. Say why, so the team can learn from it." confirmLabel="Mark lost" danger
                busy={busy} error={error} onCancel={() => setLost(null)} onConfirm={() => reason.trim() && void stage(lost, "lost", reason.trim())}>
                <Field label="Reason">{(id) => <input id={id} className="input" maxLength={500} value={reason} onChange={(e) => setReason(e.target.value)} autoFocus />}</Field>
              </ConfirmDialog>
            )}
            {winning && <WinForm deal={winning} onClose={() => setWinning(null)} onWon={(projectId) => { setWinning(null); toast(`${winning.title} won. Client and project created.`); router.push(`/projects/${projectId}`); }} />}
          </>
        );
      }}
    </Async>
  );
}

function WinForm({ deal, onClose, onWon }: { deal: Deal; onClose: () => void; onWon: (projectId: string) => void }) {
  const members = useApi<Page<Member>>("/members", { limit: 100, status: "active" });
  const [f, setF] = useState({ name: deal.title, billing_type: "fixed", budget_amount: deal.amount, hourly_rate: "", template: "blank", owner_id: deal.owner.id, renewal_date: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const project: Record<string, unknown> = { name: f.name, billing_type: f.billing_type, template: f.template, owner_id: f.owner_id };
    if (f.billing_type === "hourly") project.hourly_rate = f.hourly_rate || null;
    else project.budget_amount = f.budget_amount || null;
    try {
      const res = await post<{ project: { id: string } }>(`/deals/${deal.id}/win`, { expected_version: deal.version, project, renewal_date: f.renewal_date || null },
        { idempotencyKey: key });
      onWon(res.project.id);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  return (
    <Modal wide title={`Win ${deal.title}`} subtitle="One step: the deal is won, the client is created, the kickoff project starts and the contact becomes a customer." onClose={onClose}
      footer={<><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" form="win-form" disabled={busy}>{busy ? "Winning…" : "Win deal"}</button></>}>
      <form id="win-form" className="form-grid" onSubmit={submit} noValidate>
        <Field label="Kickoff project name" error={fe["project.name"]} className="full">{(id, inv) => <input id={id} className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Billing" error={fe["project.billing_type"]}>{(id) => <select id={id} className="select" value={f.billing_type} onChange={(e) => setF({ ...f, billing_type: e.target.value })}>
          {["fixed", "hourly", "retainer"].map((b) => <option key={b} value={b}>{label(b)}</option>)}</select>}</Field>
        {f.billing_type === "hourly"
          ? <Field label="Hourly rate" error={fe["project.hourly_rate"]}>{(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.hourly_rate} onChange={(e) => setF({ ...f, hourly_rate: e.target.value })} aria-invalid={inv} />}</Field>
          : <Field label="Budget" error={fe["project.budget_amount"]}>{(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.budget_amount} onChange={(e) => setF({ ...f, budget_amount: e.target.value })} aria-invalid={inv} />}</Field>}
        <Field label="Template" hint="Website: 12 tasks · Mobile app: 15 tasks">{(id) => <select id={id} className="select" value={f.template} onChange={(e) => setF({ ...f, template: e.target.value })}>
          <option value="blank">Blank</option><option value="website_standard">Website (standard)</option><option value="mobile_app_standard">Mobile app (standard)</option></select>}</Field>
        <Field label="Project owner" error={fe["project.owner_id"]}>{(id) => <select id={id} className="select" value={f.owner_id} onChange={(e) => setF({ ...f, owner_id: e.target.value })}>
          {(members.data?.items ?? [{ user_id: deal.owner.id, name: deal.owner.name }]).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>}</Field>
        <Field label="Renewal date (optional)" error={fe.renewal_date}>{(id, inv) => <input id={id} className="input" type="date" value={f.renewal_date} onChange={(e) => setF({ ...f, renewal_date: e.target.value })} aria-invalid={inv} />}</Field>
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}
