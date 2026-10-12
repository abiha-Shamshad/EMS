"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { ContactForm } from "@/components/forms/ContactForm";
import { Card, Empty, ErrorState, Loading, LoadMore, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { label, relative } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { ContactRow } from "@/lib/types";
import { usePost } from "@/lib/useApi";

const STAGES = ["lead", "qualified", "opportunity", "customer", "churned", "disqualified"];

/** Screen 37 - contacts and leads (API-046 search, API-045 create). */
export default function ContactsPage() {
  const router = useRouter();
  const { can, me } = useSession();
  const canRead = can("crm.manage") || me.active_org.role === "cfo";
  const [text, setText] = useState("");
  const [query, setQuery] = useState<string | null>(null);
  const [stage, setStage] = useState("");
  const body = { query, lifecycle_stage: stage ? [stage] : null, limit: 25 };
  const res = usePost<{ items: ContactRow[]; next_cursor: string | null }>(canRead ? "/contacts/search" : null, body);
  const [extra, setExtra] = useState<ContactRow[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [moreError, setMoreError] = useState<ApiError | null>(null);
  const [adding, setAdding] = useState(false);
  if (!canRead) return <NoAccess message="Only sales leadership, managers and the CFO can open the CRM." />;

  const reset = () => { setExtra([]); setCursor(undefined); };
  const next = cursor === undefined ? res.data?.next_cursor : cursor;
  async function more() {
    try {
      const p = await post<{ items: ContactRow[]; next_cursor: string | null }>("/contacts/search", { ...body, cursor: next });
      setExtra((e) => [...e, ...p.items]);
      setCursor(p.next_cursor);
    } catch (e) {
      setMoreError(e as ApiError);
    }
  }
  const items = [...(res.data?.items ?? []), ...extra];

  return (
    <>
      <PageHeader title="Contacts & leads" subtitle="Search by name, email or company" actions={<>
        <form className="row gap-sm" onSubmit={(e) => { e.preventDefault(); reset(); setQuery(text.trim().length >= 2 ? text.trim() : null); }}>
          <input className="input" style={{ width: 240 }} placeholder="Search (2+ characters)" value={text} onChange={(e) => setText(e.target.value)} aria-label="Search" />
          <button className="btn ghost">Search</button>
        </form>
        <select className="select" style={{ width: 160 }} value={stage} onChange={(e) => { reset(); setStage(e.target.value); }} aria-label="Stage">
          <option value="">All stages</option>{STAGES.map((s) => <option key={s} value={s}>{label(s)}</option>)}</select>
        {can("crm.manage") && <button className="btn" onClick={() => setAdding(true)}>New contact</button>}
      </>} />
      <Card flush>
        {res.error && !res.data ? <div style={{ padding: 20 }}><ErrorState error={res.error} retry={res.reload} /></div> : !res.data ? <Loading /> :
          items.length === 0 ? <Empty title="No contacts match" /> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>Name</th><th>Company</th><th>Stage</th><th>Owner</th><th>Last activity</th></tr></thead>
              <tbody>{items.map((c) => (
                <tr key={c.id} className="clickable" onClick={() => router.push(`/crm/contacts/${c.id}`)}>
                  <td><b>{c.name}</b></td><td>{c.company ?? "—"}</td><td><StatusBadge value={c.lifecycle_stage} /></td><td>{c.owner ?? "—"}</td><td>{relative(c.last_activity_at)}</td>
                </tr>
              ))}</tbody>
            </table></div>
          )}
        {moreError && <div style={{ padding: 12 }}><ErrorState error={moreError} /></div>}
        <LoadMore cursor={next} onMore={() => void more()} />
      </Card>
      {adding && <ContactForm onClose={() => setAdding(false)} onCreated={(id) => router.push(`/crm/contacts/${id}`)} />}
    </>
  );
}
