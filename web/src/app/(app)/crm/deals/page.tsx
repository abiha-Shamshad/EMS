"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card, Empty, ErrorState, Loading, LoadMore, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, get } from "@/lib/api";
import { date, label, money, relative } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Deal = { id: string; title: string; stage: string; amount: string; currency: string; expected_close: string | null; last_activity_at: string;
  owner: { id: string; name: string }; contact: { id: string; name: string }; company: string | null; stale: boolean };

/** All deals as a table (GET /deals), filterable by stage. The board view is /crm/pipeline. */
export default function DealsPage() {
  const router = useRouter();
  const { can, me } = useSession();
  const canRead = can("crm.manage") || me.active_org.role === "cfo";
  const [stage, setStage] = useState("");
  const first = useApi<Page<Deal>>(canRead ? "/deals" : null, { stage: stage || null, limit: 50 });
  const [more, setMore] = useState<{ stage: string; items: Deal[]; cursor: string | null } | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  if (!canRead) return <NoAccess message="Only sales leadership, managers and the CFO can see deals." />;

  const extra = more?.stage === stage ? more : null;
  const items = [...(first.data?.items ?? []), ...(extra?.items ?? [])];
  const cursor = extra ? extra.cursor : first.data?.next_cursor;
  async function loadMore() {
    try {
      const p = await get<Page<Deal>>("/deals", { stage: stage || null, limit: 50, cursor });
      setMore({ stage, items: [...(extra?.items ?? []), ...p.items], cursor: p.next_cursor });
    } catch (e) {
      setError(e as ApiError);
    }
  }

  return (
    <>
      <PageHeader title="Deals" subtitle="Every opportunity, most recently active first" actions={<>
        <select className="select" style={{ width: 170 }} value={stage} onChange={(e) => setStage(e.target.value)} aria-label="Stage">
          <option value="">All stages</option>{["new", "qualified", "proposal", "negotiation", "won", "lost"].map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
        <button className="btn ghost" onClick={() => router.push("/crm/pipeline")}>Board view</button>
      </>} />
      <Card flush>
        {first.error && !first.data ? <div style={{ padding: 20 }}><ErrorState error={first.error} retry={first.reload} /></div> : !first.data ? <Loading /> :
          items.length === 0 ? <Empty title="No deals" /> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Deal</th><th>Company / contact</th><th>Stage</th><th className="num">Amount</th><th>Owner</th><th>Expected close</th><th>Last activity</th></tr></thead>
              <tbody>{items.map((d) => (
                <tr key={d.id} className="clickable" onClick={() => router.push(`/crm/contacts/${d.contact.id}`)}>
                  <td><b>{d.title}</b></td><td>{d.company ?? d.contact.name}</td><td><StatusBadge value={d.stage} /></td>
                  <td className="num">{money(d.amount, d.currency)}</td><td>{d.owner.name}</td><td>{date(d.expected_close)}</td>
                  <td>{d.stale ? <span className="badge danger">{relative(d.last_activity_at)}</span> : relative(d.last_activity_at)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        {error && <div style={{ padding: 12 }}><ErrorState error={error} /></div>}
        <LoadMore cursor={cursor} onMore={() => void loadMore()} />
      </Card>
    </>
  );
}
