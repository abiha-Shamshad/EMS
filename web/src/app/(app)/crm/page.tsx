"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { ContactForm } from "@/components/forms/ContactForm";
import { Card, Empty, ErrorState, Loading, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { label, money, relative, sumMoney } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { ContactRow } from "@/lib/types";
import { useApi, usePost } from "@/lib/useApi";

type Pipeline = { currency: string; stages: { stage: string; count: number; amount: string }[]; weighted_open: string;
  won_this_month: { count: number; amount: string }; stale_count: number };

/** Screen 36 - CRM dashboard: pipeline totals (API-049) and recent contacts (API-046). */
export default function CrmDashboardPage() {
  const router = useRouter();
  const { can, me } = useSession();
  const canRead = can("crm.manage") || me.active_org.role === "cfo";
  const [currency, setCurrency] = useState<string | null>(null);
  const pipe = useApi<Pipeline>(canRead ? "/deals/pipeline" : null, { currency });
  const recent = usePost<{ items: ContactRow[] }>(canRead ? "/contacts/search" : null, { limit: 8 });
  const [adding, setAdding] = useState(false);
  if (!canRead) return <NoAccess message="Only sales leadership, managers and the CFO can open the CRM." />;

  const choices = (pipe.error?.details.currencies as string[] | undefined) ?? null;
  return (
    <>
      <PageHeader title="CRM" subtitle="Pipeline, clients and the people behind them" actions={<>
        <Link className="btn ghost" href="/crm/contacts">Contacts</Link>
        <Link className="btn ghost" href="/crm/deals">Deals</Link>
        <Link className="btn ghost" href="/crm/clients">Clients</Link>
        <Link className="btn ghost" href="/crm/pipeline">Pipeline board</Link>
        {can("crm.manage") && <button className="btn" onClick={() => setAdding(true)}>New contact</button>}
      </>} />
      {choices && (
        <div className="alert info row gap">Deals exist in several currencies. Show:
          {choices.map((c) => <button key={c} className="btn sm ghost" onClick={() => setCurrency(c)}>{c}</button>)}</div>
      )}
      {pipe.error && !choices ? <ErrorState error={pipe.error} retry={pipe.reload} /> : !pipe.data ? (choices ? null : <Loading />) : (
        <>
          <div className="grid grid-4">
            <div className="card stat"><span className="stat-label">Open pipeline</span>
              <span className="stat-value">{money(sumMoney(pipe.data.stages.map((s) => s.amount)), pipe.data.currency)}</span>
              <span className="stat-foot">{pipe.data.stages.reduce((n, s) => n + s.count, 0)} open deals</span></div>
            <div className="card stat"><span className="stat-label">Weighted value</span><span className="stat-value">{money(pipe.data.weighted_open, pipe.data.currency)}</span>
              <span className="stat-foot">stage probability × amount</span></div>
            <div className="card stat"><span className="stat-label">Won this month</span><span className="stat-value">{money(pipe.data.won_this_month.amount, pipe.data.currency)}</span>
              <span className="stat-foot">{pipe.data.won_this_month.count} deals</span></div>
            <Link href="/crm/pipeline" className="card stat" style={{ color: "inherit", textDecoration: "none" }}><span className="stat-label">Stale deals</span>
              <span className="stat-value">{pipe.data.stale_count}</span><span className="stat-foot">no activity for 14+ days</span></Link>
          </div>
          <Card title="Pipeline by stage" subtitle={`Amounts in ${pipe.data.currency}`}>
            <div className="grid grid-4">
              {pipe.data.stages.map((s) => (
                <div key={s.stage} className="stack-sm"><StatusBadge value={s.stage} /><b style={{ fontSize: 20 }}>{money(s.amount, pipe.data!.currency)}</b>
                  <span className="muted small">{s.count} deal{s.count === 1 ? "" : "s"}</span></div>
              ))}
            </div>
          </Card>
        </>
      )}
      <Card title="Recently active contacts" actions={<Link href="/crm/contacts" className="btn ghost sm">All contacts</Link>} flush>
        {recent.error ? <div style={{ padding: 20 }}><ErrorState error={recent.error} retry={recent.reload} /></div> : !recent.data ? <Loading /> :
          recent.data.items.length === 0 ? <Empty title="No contacts yet">Add a contact or promote a prospect from the Lead Hunter.</Empty> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Name</th><th>Company</th><th>Stage</th><th>Owner</th><th>Last activity</th></tr></thead>
              <tbody>{recent.data.items.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => router.push(`/crm/contacts/${c.id}`)}>
                  <td><b>{c.name}</b></td><td>{c.company ?? "—"}</td><td><StatusBadge value={c.lifecycle_stage} /></td><td>{c.owner ?? "—"}</td><td>{relative(c.last_activity_at)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
      </Card>
      {adding && <ContactForm onClose={() => setAdding(false)} onCreated={(id) => router.push(`/crm/contacts/${id}`)} />}
      <p className="muted small">Lifecycle: {["lead", "qualified", "opportunity", "customer"].map(label).join(" → ")}</p>
    </>
  );
}
