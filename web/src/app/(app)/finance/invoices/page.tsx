"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { Async, Card, Empty, Field, FormError, Modal, NoAccess, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { date, label, money, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Invoice = { id: string; number: string; client_id: string; client: string; project: string | null; amount: string; paid: string; outstanding: string;
  currency: string; issued_on: string; due_on: string; status: string };
type Client = { id: string; name: string };
type Project = { id: string; name: string; client: string | null };

/** Invoice and payment records (API-053/054). EMS records money; it does not send invoices or collect payments in Release 1. */
export default function InvoicesPage() {
  return <Suspense><Invoices /></Suspense>;
}

function Invoices() {
  const toast = useToast();
  const { can, timeZone } = useSession();
  const clientFilter = useSearchParams().get("client");
  const [status, setStatus] = useState("");
  const list = useApi<{ items: Invoice[] }>(can("finance.manage") ? "/invoices" : null, { status: status || null, client_id: clientFilter, limit: 100 });
  const clients = useApi<{ items: Client[] }>(can("finance.manage") ? "/clients" : null);
  const projects = useApi<{ items: Project[] }>(can("finance.manage") ? "/projects" : null, { limit: 100 });
  const [recording, setRecording] = useState(false);
  const [paying, setPaying] = useState<Invoice | null>(null);
  if (!can("finance.manage")) return <NoAccess message="Only the CEO and CFO can record invoices and payments." />;
  const todayStr = today(timeZone);

  return (
    <>
      <PageHeader title="Invoices" subtitle="Record invoices you issued and payments you received. Overdue = unpaid past its due date."
        actions={<>
          <select className="select" style={{ width: 170 }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
            <option value="">All statuses</option>{["sent", "partially_paid", "paid", "void"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
          <button className="btn" onClick={() => setRecording(true)}>Record invoice</button>
        </>} />
      <Card flush>
        <Async state={list}>
          {(l) => l.items.length === 0 ? <Empty title="No invoices recorded">Record the invoices you send so EMS can track what is outstanding.</Empty> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Number</th><th>Client</th><th>Issued</th><th>Due</th><th className="num">Amount</th><th className="num">Outstanding</th><th>Status</th><th /></tr></thead>
              <tbody>{l.items.map((i) => {
                const overdue = i.status !== "paid" && i.status !== "void" && i.due_on < todayStr;
                return (
                  <tr key={i.id}>
                    <td><b>{i.number}</b>{i.project && <div className="muted small">{i.project}</div>}</td><td>{i.client}</td><td>{date(i.issued_on)}</td>
                    <td>{date(i.due_on)}{overdue && <span className="badge danger" style={{ marginLeft: 6 }}>Overdue</span>}</td>
                    <td className="num">{money(i.amount, i.currency)}</td><td className="num">{money(i.outstanding, i.currency)}</td><td><StatusBadge value={i.status} /></td>
                    <td className="num">{i.status !== "paid" && i.status !== "void" && <button className="btn sm ghost" onClick={() => setPaying(i)}>Record payment</button>}</td>
                  </tr>
                );
              })}</tbody>
            </table></div>
          )}
        </Async>
      </Card>
      {recording && <InvoiceForm clients={clients.data?.items ?? []} projects={projects.data?.items ?? []} defaultDate={todayStr}
        onClose={() => setRecording(false)} onSaved={() => { setRecording(false); toast("Invoice recorded"); list.reload(); }} />}
      {paying && <PaymentForm invoice={paying} defaultDate={todayStr} onClose={() => setPaying(null)}
        onSaved={(s) => { setPaying(null); toast(`Payment recorded · invoice ${label(s)}`); list.reload(); }} />}
    </>
  );
}

function InvoiceForm({ clients, projects, defaultDate, onClose, onSaved }: {
  clients: Client[]; projects: Project[]; defaultDate: string; onClose: () => void; onSaved: () => void;
}) {
  const [f, setF] = useState({ client_id: "", project_id: "", number: "", amount: "", currency: "USD", issued_on: defaultDate, due_on: defaultDate });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};
  const client = clients.find((c) => c.id === f.client_id);
  const clientProjects = projects.filter((p) => client && p.client === client.name);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/invoices", { ...f, project_id: f.project_id || null, time_entry_ids: [] }, { idempotencyKey: key });
      onSaved();
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }
  return (
    <Modal title="Record invoice" onClose={onClose} footer={<><button className="btn ghost" onClick={onClose}>Cancel</button>
      <button className="btn" form="inv-form" disabled={busy || !f.client_id || !f.number || !f.amount}>{busy ? "Saving…" : "Record invoice"}</button></>}>
      <form id="inv-form" className="form-grid" onSubmit={submit} noValidate>
        <Field label="Client" error={fe.client_id} className="full" hint={clients.length === 0 ? "Clients are created when a deal is won" : undefined}>
          {(id, inv) => <select id={id} className="select" value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value, project_id: "" })} aria-invalid={inv}>
            <option value="">Choose a client…</option>{clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>}</Field>
        <Field label="Project (optional)" error={fe.project_id} className="full">
          {(id) => <select id={id} className="select" value={f.project_id} onChange={(e) => setF({ ...f, project_id: e.target.value })} disabled={!client}>
            <option value="">No project</option>{clientProjects.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select>}</Field>
        <Field label="Invoice number" error={fe.number}>{(id, inv) => <input id={id} className="input" value={f.number} onChange={(e) => setF({ ...f, number: e.target.value })} aria-invalid={inv} placeholder="INV-2026-1048" />}</Field>
        <Field label="Amount" error={fe.amount} hint="Decimal, e.g. 2500.00">{(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Currency" error={fe.currency}>{(id, inv) => <input id={id} className="input" maxLength={3} value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })} aria-invalid={inv} />}</Field>
        <Field label="Issued on" error={fe.issued_on}>{(id, inv) => <input id={id} className="input" type="date" value={f.issued_on} onChange={(e) => setF({ ...f, issued_on: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Due on" error={fe.due_on}>{(id, inv) => <input id={id} className="input" type="date" min={f.issued_on} value={f.due_on} onChange={(e) => setF({ ...f, due_on: e.target.value })} aria-invalid={inv} />}</Field>
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}

function PaymentForm({ invoice, defaultDate, onClose, onSaved }: { invoice: Invoice; defaultDate: string; onClose: () => void; onSaved: (status: string) => void }) {
  const [f, setF] = useState({ amount: invoice.outstanding, received_on: defaultDate, method: "bank_transfer" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ invoice_status: string }>(`/invoices/${invoice.id}/payments`, f, { idempotencyKey: key });
      onSaved(r.invoice_status);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }
  return (
    <Modal title={`Payment for ${invoice.number}`} subtitle={`Outstanding ${money(invoice.outstanding, invoice.currency)}`} onClose={onClose}
      footer={<><button className="btn ghost" onClick={onClose}>Cancel</button><button className="btn" form="pay-form" disabled={busy}>{busy ? "Saving…" : "Record payment"}</button></>}>
      <form id="pay-form" className="form-grid" onSubmit={submit} noValidate>
        <Field label="Amount" error={fe.amount}>{(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Received on" error={fe.received_on}>{(id, inv) => <input id={id} className="input" type="date" value={f.received_on} onChange={(e) => setF({ ...f, received_on: e.target.value })} aria-invalid={inv} />}</Field>
        <Field label="Method" className="full">{(id) => <select id={id} className="select" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })}>
          {["bank_transfer", "card", "cash", "cheque", "other"].map((m) => <option key={m} value={m}>{label(m)}</option>)}</select>}</Field>
        <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
      </form>
    </Modal>
  );
}
