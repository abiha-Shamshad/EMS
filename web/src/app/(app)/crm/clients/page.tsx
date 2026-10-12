"use client";

import Link from "next/link";
import { useState } from "react";

import { Async, Card, Empty, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { date, label } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Client = { id: string; name: string; status: string; since: string; renewal_date: string | null; origin_deal: string };

/** Clients created by winning deals (GET /clients). Status moves: onboarding -> active (first task active) -> at risk (rules). */
export default function ClientsPage() {
  const { can } = useSession();
  const [status, setStatus] = useState("");
  const list = useApi<{ items: Client[] }>(can("crm.manage") || can("finance.manage") ? "/clients" : null, { status: status || null });
  if (!can("crm.manage") && !can("finance.manage")) return <NoAccess message="Only sales, finance and leadership can see clients." />;
  return (
    <>
      <PageHeader title="Clients" subtitle="Every client starts from a won deal" actions={<>
        <select className="select" style={{ width: 170 }} value={status} onChange={(e) => setStatus(e.target.value)} aria-label="Status">
          <option value="">All statuses</option>{["onboarding", "active", "at_risk", "churned"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
        <Link className="btn ghost" href="/crm/pipeline">Pipeline</Link>
      </>} />
      <Card flush>
        <Async state={list}>
          {(l) => l.items.length === 0 ? <Empty title="No clients yet">Win a deal on the pipeline board to create the client and its kickoff project.</Empty> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Client</th><th>Status</th><th>Client since</th><th>Renewal</th><th>From deal</th>{can("finance.manage") && <th />}</tr></thead>
              <tbody>{l.items.map((c) => (
                <tr key={c.id}>
                  <td><b>{c.name}</b></td><td><StatusBadge value={c.status} /></td><td>{date(c.since)}</td><td>{date(c.renewal_date)}</td><td>{c.origin_deal}</td>
                  {can("finance.manage") && <td className="num"><Link className="btn sm ghost" href={`/finance/invoices?client=${c.id}`}>Invoices</Link></td>}
                </tr>
              ))}</tbody>
            </table></div>
          )}
        </Async>
      </Card>
    </>
  );
}
