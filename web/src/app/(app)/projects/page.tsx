"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Async, Card, Empty, Field, FormError, Modal, PageHeader, Progress, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { label, money } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Project = {
  id: string; name: string; client: string | null; status: string; billing_type: string; progress_pct: number;
  tasks: Record<"todo" | "active" | "review" | "done", number>; overdue: number;
  budget: { amount: string | null; cost_to_date: string; currency: string | null; ratio: string | null; rates_missing?: number } | null;
};
type Client = { id: string; name: string; status: string };

/** Screen 33 - projects dashboard and list (API-038), create project (API-039). Members see the projects they are on. */
export default function ProjectsPage() {
  const router = useRouter();
  const toast = useToast();
  const { me, can } = useSession();
  const [status, setStatus] = useState("");
  const list = useApi<Page<Project>>("/projects", { status: status || null, limit: 100 });
  const canClients = can("crm.manage") || can("finance.manage");
  const clients = useApi<{ items: Client[] }>(can("projects.manage") && canClients ? "/clients" : null);
  const members = useApi<Page<Member>>(can("projects.manage") ? "/members" : null, { limit: 100, status: "active" });
  const [creating, setCreating] = useState(false);
  const [f, setF] = useState({ name: "", billing_type: "internal", client_id: "", budget_amount: "", hourly_rate: "", currency: "USD", owner_id: me.user.id });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key, setKey] = useState(newIdempotencyKey);

  async function create(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    const body: Record<string, unknown> = { name: f.name, billing_type: f.billing_type, owner_id: f.owner_id };
    if (f.billing_type !== "internal") body.client_id = f.client_id || null;
    if (f.billing_type === "fixed" || f.billing_type === "retainer") { body.budget_amount = f.budget_amount || null; body.currency = f.currency; }
    if (f.billing_type === "hourly") { body.hourly_rate = f.hourly_rate || null; body.currency = f.currency; }
    try {
      const p = await post<{ id: string }>("/projects", body, { idempotencyKey: key });
      toast("Project created");
      setKey(newIdempotencyKey());
      router.push(`/projects/${p.id}`);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }
  const fe = error?.fields ?? {};

  return (
    <>
      <PageHeader title="Projects" subtitle="Progress, budget burn and overdue work" actions={<>
        <select className="select" style={{ width: 160 }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">All statuses</option>{["planned", "active", "on_hold", "completed", "cancelled"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
        {can("projects.manage") && <button className="btn" onClick={() => setCreating(true)}>New project</button>}
      </>} />
      <Async state={list}>
        {(l) => l.items.length === 0 ? <Card><Empty title="No projects yet">{can("projects.manage") ? "Create one, or win a deal in the CRM to start a kickoff project." : "Projects you are assigned to appear here."}</Empty></Card> : (
          <div className="grid grid-3">
            {l.items.map((p) => {
              const total = p.tasks.todo + p.tasks.active + p.tasks.review + p.tasks.done;
              return (
                <button key={p.id} className="card stack-sm" style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit" }} onClick={() => router.push(`/projects/${p.id}`)}>
                  <div className="row between gap"><b style={{ fontSize: 15 }}>{p.name}</b><StatusBadge value={p.status} /></div>
                  <span className="muted small">{p.client ?? "Internal"} · {label(p.billing_type)}</span>
                  <div className="row gap"><div className="grow"><Progress ratio={total ? p.progress_pct / 100 : 0} /></div><span className="small">{p.progress_pct}%</span></div>
                  <span className="small muted">{p.tasks.todo} to do · {p.tasks.active} active · {p.tasks.review} review · {p.tasks.done} done</span>
                  <div className="row gap wrap">
                    {p.overdue > 0 && <span className="badge danger">{p.overdue} overdue</span>}
                    {p.budget?.amount && <span className="badge">Budget {money(p.budget.cost_to_date, p.budget.currency ?? "USD")} of {money(p.budget.amount, p.budget.currency ?? "USD")}</span>}
                  </div>
                </button>
              );
            })}
          </div>
        )}
      </Async>
      {creating && (
        <Modal title="New project" onClose={() => setCreating(false)} footer={<>
          <button className="btn ghost" onClick={() => setCreating(false)}>Cancel</button>
          <button className="btn" form="new-project" disabled={busy || !f.name}>{busy ? "Creating…" : "Create project"}</button></>}>
          <form id="new-project" className="form-grid" onSubmit={create} noValidate>
            <Field label="Name" error={fe.name} className="full">
              {(id, inv) => <input id={id} className="input" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} aria-invalid={inv} autoFocus />}
            </Field>
            <Field label="Billing" error={fe.billing_type}>
              {(id) => <select id={id} className="select" value={f.billing_type} onChange={(e) => setF({ ...f, billing_type: e.target.value })}>
                {["internal", "fixed", "hourly", "retainer"].map((b) => <option key={b} value={b}>{label(b)}</option>)}</select>}
            </Field>
            <Field label="Owner" error={fe.owner_id}>
              {(id) => <select id={id} className="select" value={f.owner_id} onChange={(e) => setF({ ...f, owner_id: e.target.value })}>
                {(members.data?.items ?? [{ user_id: me.user.id, name: me.user.name }]).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>}
            </Field>
            {f.billing_type !== "internal" && (
              <Field label="Client" error={fe.client_id} className="full" hint={canClients ? "Clients come from won deals" : "Your role cannot list clients; ask sales or finance to create client projects"}>
                {(id, inv) => <select id={id} className="select" value={f.client_id} onChange={(e) => setF({ ...f, client_id: e.target.value })} aria-invalid={inv} disabled={!canClients}>
                  <option value="">Choose a client…</option>{(clients.data?.items ?? []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select>}
              </Field>
            )}
            {(f.billing_type === "fixed" || f.billing_type === "retainer") && (
              <Field label="Budget" error={fe.budget_amount} hint="Decimal, e.g. 5000.00">
                {(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.budget_amount} onChange={(e) => setF({ ...f, budget_amount: e.target.value })} aria-invalid={inv} />}
              </Field>
            )}
            {f.billing_type === "hourly" && (
              <Field label="Hourly rate" error={fe.hourly_rate} hint="Decimal, e.g. 40.00">
                {(id, inv) => <input id={id} className="input" inputMode="decimal" value={f.hourly_rate} onChange={(e) => setF({ ...f, hourly_rate: e.target.value })} aria-invalid={inv} />}
              </Field>
            )}
            {f.billing_type !== "internal" && (
              <Field label="Currency" error={fe.currency}>
                {(id, inv) => <input id={id} className="input" maxLength={3} value={f.currency} onChange={(e) => setF({ ...f, currency: e.target.value.toUpperCase() })} aria-invalid={inv} />}
              </Field>
            )}
            <div className="full"><FormError error={error && !Object.keys(fe).length ? error : null} /></div>
          </form>
        </Modal>
      )}
    </>
  );
}
