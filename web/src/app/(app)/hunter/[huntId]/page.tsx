"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { Async, Card, Empty, Field, FormError, NoAccess, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { useSession } from "@/lib/session";
import { useApi, usePoll } from "@/lib/useApi";

type Status = { hunt_id: string; name: string; status: string; stats: Record<string, number> };
type Prospect = { id: string; domain: string; company_name: string; score: number; score_reasons: string[]; public_emails: string[]; source_url: string; status: string };
type Draft = { subject: string; body: string; fields_used: string[] };

/** Screen 42 - results and scoring (API-056/057), with screen 43 lead details: promote (API-058), outreach draft (API-059), suppress (API-060). */
export default function HuntResultsPage() {
  const { can } = useSession();
  return can("hunter.use") ? <HuntResults /> : <><PageHeader title="Lead Hunter" /><NoAccess /></>;
}

function HuntResults() {
  const { huntId } = useParams<{ huntId: string }>();
  const router = useRouter();
  const toast = useToast();
  const { me, can } = useSession();
  const status = useApi<Status>(`/hunts/${huntId}`);
  const [minScore, setMinScore] = useState(0);
  const prospects = useApi<{ items: Prospect[] }>(`/hunts/${huntId}/prospects`, { min_score: minScore, limit: 100 });
  usePoll(() => { if (status.data && ["queued", "running"].includes(status.data.status)) { status.reload(); prospects.reload(); } }, 5000);
  const [selected, setSelected] = useState<Prospect | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [form, setForm] = useState({ template: "intro_services", sender_name: me.user.name, offer: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  async function act<T>(fn: () => Promise<T>, done: (r: T) => void) {
    setBusy(true);
    setError(null);
    try {
      done(await fn());
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }
  const pick = (p: Prospect) => { setSelected(p); setDraft(null); setError(null); };

  return (
    <>
      <Async state={status}>
        {(s) => (
          <>
            <PageHeader title={s.name} subtitle={<><Link href="/hunter">Lead Hunter</Link> · <StatusBadge value={s.status} />{["queued", "running"].includes(s.status) && " · refreshing every 5 seconds"}</>}
              actions={<select className="select" style={{ width: 170 }} value={minScore} onChange={(e) => setMinScore(Number(e.target.value))} aria-label="Minimum score">
                {[0, 50, 70, 80].map((n) => <option key={n} value={n}>{n ? `Score ${n}+` : "All scores"}</option>)}</select>} />
            <div className="grid grid-4">
              {[["Domains", "domains"], ["Pages fetched", "fetched_pages"], ["Blocked by robots.txt", "robots_disallowed"], ["Unreachable", "unreachable"],
                ["Prospects", "prospects"], ["Already in CRM", "already_in_crm"], ["Skipped (do-not-contact)", "suppressed"]].filter(([, k]) => k !== "suppressed" || k! in s.stats).map(([t, k]) => (
                <div key={k} className="card stat"><span className="stat-label">{t}</span><span className="stat-value">{s.stats[k!] ?? 0}</span></div>
              ))}
            </div>
          </>
        )}
      </Async>
      <div className="grid grid-3">
        <Card title="Prospects" subtitle="Every point of the score has a reason" className="span-2" flush>
          <Async state={prospects}>
            {(p) => p.items.length === 0 ? <Empty title={status.data?.status === "completed" ? "No prospects matched" : "Crawling…"}>Results appear as each site is scored.</Empty> : (
              <div className="table-wrap"><table className="table">
                <thead><tr><th>Company</th><th className="num">Score</th><th>Why</th><th>Status</th></tr></thead>
                <tbody>{p.items.map((x) => (
                  <tr key={x.id} className="clickable" onClick={() => pick(x)} style={selected?.id === x.id ? { background: "var(--primary-soft)" } : undefined}>
                    <td><b>{x.company_name}</b><div className="muted small">{x.domain}</div></td>
                    <td className="num"><span className={`badge ${x.score >= 80 ? "success" : x.score >= 50 ? "warning" : ""}`}>{x.score}</span></td>
                    <td className="small">{x.score_reasons.join(" · ") || <span className="muted">No signals matched</span>}</td>
                    <td><StatusBadge value={x.status} /></td>
                  </tr>
                ))}</tbody>
              </table></div>
            )}
          </Async>
        </Card>
        <Card title={selected ? selected.company_name : "Lead details"} subtitle={selected ? selected.domain : "Choose a prospect"}>
          {!selected ? <p className="muted">Pick a prospect to see its signals, add it to the CRM or draft an email.</p> : (
            <div className="stack">
              <dl className="kv" style={{ gridTemplateColumns: "110px 1fr" }}>
                <dt>Score</dt><dd>{selected.score} / 100</dd>
                <dt>Public emails</dt><dd>{selected.public_emails.join(", ") || "None listed"}</dd>
                <dt>Source</dt><dd><a href={selected.source_url} target="_blank" rel="noreferrer noopener">{selected.source_url}</a></dd>
                <dt>Status</dt><dd><StatusBadge value={selected.status} /></dd>
              </dl>
              <div className="row gap wrap">
                {can("crm.manage") && <button className="btn" disabled={busy || selected.status === "suppressed"} onClick={() => void act(
                  () => post<{ contact_id: string }>(`/prospects/${selected.id}/promote`, {}),
                  (r) => { toast(`${selected.company_name} added to the CRM`); router.push(`/crm/contacts/${r.contact_id}`); })}>Add to CRM</button>}
                <button className="btn ghost" disabled={busy} onClick={() => void act(
                  () => post<{ prospects_suppressed: number }>("/suppressions", { kind: "domain", value: selected.domain, reason: "manual" }),
                  () => { toast(`${selected.domain} will not be contacted`); setSelected({ ...selected, status: "suppressed" }); prospects.reload(); })}>Do not contact</button>
              </div>
              <hr style={{ border: 0, borderTop: "1px solid var(--border)", margin: 0 }} />
              <h3 className="h3">Outreach draft</h3>
              <p className="muted small">EMS never sends email. Copy the draft into your own mail client; it always ends with an opt-out line.</p>
              <Field label="Template">{(id) => <select id={id} className="select" value={form.template} onChange={(e) => setForm({ ...form, template: e.target.value })}>
                <option value="intro_services">Introduce our services</option><option value="partnership">Partnership idea</option><option value="follow_up">Follow up</option></select>}</Field>
              <Field label="What you offer" error={error?.fields.offer}>{(id, inv) => <input id={id} className="input" placeholder="e.g. website maintenance" value={form.offer}
                onChange={(e) => setForm({ ...form, offer: e.target.value })} aria-invalid={inv} />}</Field>
              <Field label="Sender name">{(id) => <input id={id} className="input" value={form.sender_name} onChange={(e) => setForm({ ...form, sender_name: e.target.value })} />}</Field>
              <button className="btn ghost" disabled={busy || form.offer.trim().length < 2} onClick={() => void act(() => post<Draft>(`/prospects/${selected.id}/outreach-draft`, form), setDraft)}>Create draft</button>
              <FormError error={error && !error.fields.offer ? error : null} />
              {draft && (
                <div className="stack-sm">
                  <b>{draft.subject}</b>
                  <pre className="code" style={{ whiteSpace: "pre-wrap", background: "var(--surface-2)", color: "var(--text)" }}>{draft.body}</pre>
                  <button className="btn sm" onClick={() => navigator.clipboard.writeText(`Subject: ${draft.subject}\n\n${draft.body}`).then(() => toast("Draft copied"))}>Copy draft</button>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
