"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Async, Card, Empty, Field, FormError, Modal, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { dateTime, label, money } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Contact = {
  id: string; name: string; email: string | null; phone?: string | null; company: { id: string; name: string } | null; lifecycle_stage: string;
  owner?: string | null; source?: string; deals: { id: string; title: string; stage: string; amount: string; currency: string }[];
  activities: { kind: string; note: string | null; occurred_at: string; actor: string | null }[];
  related: { kind: string; label: string; via: string[] }[];
};

const toLocalInput = (d: Date) => new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);

/** Screen 38 - contact / lead details (API-047) with activities (API-052), deals (API-048) and related records from graph memory. */
export default function ContactDetailPage() {
  const { contactId } = useParams<{ contactId: string }>();
  const toast = useToast();
  const { can, timeZone } = useSession();
  const contact = useApi<Contact>(`/contacts/${contactId}`);
  const [act, setAct] = useState({ kind: "call", note: "", occurred_at: toLocalInput(new Date()) });
  const [actKey, setActKey] = useState(newIdempotencyKey);
  const [dealOpen, setDealOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function logActivity(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/activities", { entity_type: "contact", entity_id: contactId, kind: act.kind, note: act.note || null, occurred_at: new Date(act.occurred_at).toISOString() },
        { idempotencyKey: actKey });
      toast("Activity logged");
      setAct({ ...act, note: "" });
      setActKey(newIdempotencyKey());
      contact.reload();
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Async state={contact}>
      {(c) => (
        <>
          <PageHeader title={c.name} subtitle={<><Link href="/crm/contacts">Contacts</Link> · {c.company?.name ?? "No company"} · <StatusBadge value={c.lifecycle_stage} /></>}
            actions={can("crm.manage") && <button className="btn" onClick={() => setDealOpen(true)}>New deal</button>} />
          <div className="grid grid-3">
            <Card title="Details">
              <dl className="kv">
                <dt>Email</dt><dd>{c.email ? <a href={`mailto:${c.email}`}>{c.email}</a> : "—"}</dd>
                {c.phone !== undefined && <><dt>Phone</dt><dd>{c.phone ?? "—"}</dd></>}
                <dt>Company</dt><dd>{c.company?.name ?? "—"}</dd>
                <dt>Stage</dt><dd>{label(c.lifecycle_stage)}</dd>
                {c.owner !== undefined && <><dt>Owner</dt><dd>{c.owner ?? "—"}</dd></>}
                {c.source && <><dt>Source</dt><dd>{label(c.source)}</dd></>}
              </dl>
            </Card>
            <Card title="Deals" className="span-2" flush>
              {c.deals.length === 0 ? <Empty title="No deals yet" /> : (
                <div className="table-wrap"><table className="table">
                  <thead><tr><th>Deal</th><th>Stage</th><th className="num">Amount</th></tr></thead>
                  <tbody>{c.deals.map((d) => <tr key={d.id}><td>{d.title}</td><td><StatusBadge value={d.stage} /></td><td className="num">{money(d.amount, d.currency)}</td></tr>)}</tbody>
                </table></div>
              )}
            </Card>
            <Card title="Activity" className="span-2">
              {can("crm.manage") && (
                <form className="row gap wrap" onSubmit={logActivity} style={{ marginBottom: 14, alignItems: "flex-end" }}>
                  <select className="select" style={{ width: 130 }} value={act.kind} onChange={(e) => setAct({ ...act, kind: e.target.value })} aria-label="Kind">
                    {["call", "email", "meeting", "note"].map((k) => <option key={k} value={k}>{label(k)}</option>)}</select>
                  <input className="input" type="datetime-local" style={{ width: 210 }} value={act.occurred_at} max={toLocalInput(new Date())}
                    onChange={(e) => setAct({ ...act, occurred_at: e.target.value })} aria-label="When" />
                  <input className="input grow" maxLength={2000} placeholder="What happened?" value={act.note} onChange={(e) => setAct({ ...act, note: e.target.value })} aria-label="Note" />
                  <button className="btn" disabled={busy}>Log</button>
                </form>
              )}
              <FormError error={error} />
              {c.activities.length === 0 ? <p className="muted">No activity yet. Logging a call or meeting also resets a deal&apos;s stale timer.</p> : (
                <div className="list">{c.activities.map((a, i) => (
                  <div key={i} className="list-item"><StatusBadge value={a.kind} /><div className="grow">{a.note ?? <span className="muted">No note</span>}
                    <div className="muted small">{dateTime(a.occurred_at, timeZone)}{a.actor ? ` · ${a.actor}` : ""}</div></div></div>
                ))}</div>
              )}
            </Card>
            <Card title="Related" subtitle="From graph memory">
              {c.related.length === 0 ? <p className="muted">Nothing linked yet. Winning a deal links the client and project.</p> : (
                <div className="stack-sm">{c.related.map((r) => (
                  <div key={`${r.kind}-${r.label}`}><span className="badge primary">{label(r.kind)}</span> {r.label}<div className="muted small">via {r.via.map(label).join(" → ")}</div></div>
                ))}</div>
              )}
            </Card>
          </div>
          {dealOpen && <DealForm contactId={c.id} onClose={() => setDealOpen(false)} onCreated={() => { setDealOpen(false); toast("Deal created"); contact.reload(); }} />}
        </>
      )}
    </Async>
  );
}

function DealForm({ contactId, onClose, onCreated }: { contactId: string; onClose: () => void; onCreated: () => void }) {
  const [f, setF] = useState({ title: "", amount: "", currency: "USD", expected_close: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/deals", { contact_id: contactId, title: f.title, amount: f.amount, currency: f.currency, expected_close: f.expected_close || null }, { idempotencyKey: key });
      onCreated();
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }
  return (
    <Modal title="New deal" onClose={onClose} footer={<><button className="btn ghost" onClick={onClose}>Cancel</button>
      <button className="btn" form="deal-form" disabled={busy || !f.title || !f.amount}>{busy ? "Saving…" : "Create deal"}</button></>}>
      <form id="deal-form" className="form-grid" onSubmit={submit} noValidate>
        <Field label="Title" error={fe.title} className="full">{(id, inv) => <input id={id} className="input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} aria-invalid={inv} autoFocus />}</Field>
        <Field label="Amount" error={fe.amount} hint="Decimal, e.g. 5000.00">{(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Currency" error={fe.currency}>{(id, inv) => <input id={id} className="input" maxLength={3} value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })} aria-invalid={inv} />}</Field>
        <Field label="Expected close" error={fe.expected_close}>{(id, inv) => <input id={id} className="input" type="date" value={f.expected_close} onChange={(e) => setF({ ...f, expected_close: e.target.value })} aria-invalid={inv} />}</Field>
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}
