"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Async, Card, Empty, Field, FormError, NoAccess, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { dateTime } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi, usePoll } from "@/lib/useApi";

type Hunt = { hunt_id: string; name: string; status: string; created_at: string; created_by: string;
  stats: { domains: number; fetched_pages: number; robots_disallowed: number; unreachable: number; prospects: number; already_in_crm: number } };

/** Screen 40 - Lead Hunter dashboard: hunts and their crawl outcomes, and the do-not-contact list (API-060). */
export default function HunterDashboardPage() {
  const router = useRouter();
  const toast = useToast();
  const { can, timeZone } = useSession();
  const hunts = useApi<{ items: Hunt[] }>(can("hunter.use") ? "/hunts" : null, { limit: 50 });
  usePoll(() => { if (hunts.data?.items.some((h) => h.status === "queued" || h.status === "running")) hunts.reload(); }, 10_000);
  const [sup, setSup] = useState({ kind: "domain", value: "", reason: "opt_out" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("hunter.use")) return <NoAccess message="Only leadership and managers can use the Lead Hunter." />;

  async function suppress(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const r = await post<{ prospects_suppressed: number }>("/suppressions", sup);
      toast(`Added to the do-not-contact list${r.prospects_suppressed ? `; ${r.prospects_suppressed} prospect(s) suppressed` : ""}`);
      setSup({ ...sup, value: "" });
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  const totals = (hunts.data?.items ?? []).reduce((t, h) => ({ prospects: t.prospects + h.stats.prospects, pages: t.pages + h.stats.fetched_pages,
    blocked: t.blocked + h.stats.robots_disallowed + h.stats.unreachable }), { prospects: 0, pages: 0, blocked: 0 });
  return (
    <>
      <PageHeader title="Lead Hunter" subtitle="Crawls company websites you supply, respecting robots.txt, and scores them against your ideal customer."
        actions={<Link className="btn" href="/hunter/new">New hunt</Link>} />
      <div className="grid grid-4">
        <div className="card stat"><span className="stat-label">Hunts</span><span className="stat-value">{hunts.data?.items.length ?? "…"}</span></div>
        <div className="card stat"><span className="stat-label">Prospects found</span><span className="stat-value">{totals.prospects}</span></div>
        <div className="card stat"><span className="stat-label">Pages fetched</span><span className="stat-value">{totals.pages}</span></div>
        <div className="card stat"><span className="stat-label">Blocked by robots.txt or unreachable</span><span className="stat-value">{totals.blocked}</span></div>
      </div>
      <div className="grid grid-3">
        <Card title="Hunts" className="span-2" flush>
          <Async state={hunts}>
            {(h) => h.items.length === 0 ? <Empty title="No hunts yet" action={<Link className="btn" href="/hunter/new">Start a hunt</Link>}>Paste up to 200 company websites to score.</Empty> : (
              <div className="table-wrap"><table className="table">
                <thead><tr><th>Hunt</th><th>Status</th><th className="num">Domains</th><th className="num">Prospects</th><th className="num">In CRM</th><th>Started</th></tr></thead>
                <tbody>{h.items.map((x) => (
                  <tr key={x.hunt_id} className="clickable" onClick={() => router.push(`/hunter/${x.hunt_id}`)}>
                    <td><b>{x.name}</b><div className="muted small">by {x.created_by}</div></td><td><StatusBadge value={x.status} /></td>
                    <td className="num">{x.stats.domains}</td><td className="num">{x.stats.prospects}</td><td className="num">{x.stats.already_in_crm}</td><td>{dateTime(x.created_at, timeZone)}</td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Async>
        </Card>
        <Card title="Do-not-contact list" subtitle="Stored as a SHA-256 hash only. Blocks crawling, promotion and drafts.">
          <form className="stack" onSubmit={suppress} noValidate>
            <Field label="Kind">{(id) => <select id={id} className="select" value={sup.kind} onChange={(e) => setSup({ ...sup, kind: e.target.value })}>
              <option value="domain">Domain</option><option value="email">Email</option></select>}</Field>
            <Field label={sup.kind === "domain" ? "Domain" : "Email"} error={error?.fields.value}>
              {(id, inv) => <input id={id} className="input" value={sup.value} onChange={(e) => setSup({ ...sup, value: e.target.value })} aria-invalid={inv}
                placeholder={sup.kind === "domain" ? "example.com" : "name@example.com"} />}</Field>
            <Field label="Reason">{(id) => <select id={id} className="select" value={sup.reason} onChange={(e) => setSup({ ...sup, reason: e.target.value })}>
              <option value="opt_out">Opted out</option><option value="bounced">Bounced</option><option value="manual">Manual</option><option value="legal">Legal</option></select>}</Field>
            <FormError error={error && !error.fields.value ? error : null} />
            <button className="btn ghost" disabled={busy || !sup.value}>Add to the list</button>
          </form>
        </Card>
      </div>
    </>
  );
}
