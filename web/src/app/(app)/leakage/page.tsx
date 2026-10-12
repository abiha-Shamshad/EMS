"use client";

import { useState } from "react";

import { Async, Card, ConfirmDialog, Empty, Field, NoAccess, PageHeader, StatusBadge, Tabs, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { dateTime, label, money } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Finding = { id: string; kind: string; label: string; amount_at_risk: string | null; currency: string | null; evidence: Record<string, unknown>;
  status: string; detected_at: string };
type Findings = { totals: { open: number; amount_at_risk: string; currency: string }; items: Finding[]; next_cursor: string | null; last_scan_at: string | null; note: string };

const KINDS = ["unbilled_time", "overdue_invoice", "stale_deal", "won_without_project", "won_without_invoice", "over_budget", "idle_paid_time"];

/** Revenue leakage findings (API-065) and resolving them (API-066). Detectors run nightly at 01:00 company time. */
export default function LeakagePage() {
  const toast = useToast();
  const { can, timeZone } = useSession();
  const [status, setStatus] = useState<"open" | "resolved" | "dismissed">("open");
  const [kind, setKind] = useState("");
  const list = useApi<Findings>(can("leakage.read") ? "/leakage/findings" : null, { status, kind: kind || null, limit: 100 });
  const [acting, setActing] = useState<{ f: Finding; resolution: "resolved" | "dismissed" } | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("leakage.read")) return <NoAccess message="Only the CEO, CFO and COO can see leakage findings." />;

  async function resolve() {
    if (!acting) return;
    setBusy(true);
    setError(null);
    try {
      await post(`/leakage/findings/${acting.f.id}/resolve`, { resolution: acting.resolution, ...(note ? { note } : {}) });
      toast(`Finding ${acting.resolution}`);
      setActing(null);
      list.reload();
    } catch (e) {
      setError(e as ApiError);
      if ((e as ApiError).code === "ALREADY_RESOLVED") list.reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Revenue leakage" subtitle="Money at risk found by the nightly detectors, with the evidence behind each amount"
        actions={<select className="select" style={{ width: 210 }} value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind">
          <option value="">All kinds</option>{KINDS.map((k) => <option key={k} value={k}>{label(k)}</option>)}</select>} />
      <Tabs value={status} onChange={setStatus} options={[{ value: "open", label: "Open" }, { value: "resolved", label: "Resolved" }, { value: "dismissed", label: "Dismissed" }]} />
      <Async state={list}>
        {(d) => (
          <>
            {!d.last_scan_at ? (
              <div className="alert info">The first nightly scan has not run yet. It runs at 01:00 company time; findings appear here afterwards.</div>
            ) : (
              <div className="grid grid-3">
                <div className="card stat"><span className="stat-label">Open findings</span><span className="stat-value">{d.totals.open}</span></div>
                <div className="card stat"><span className="stat-label">Revenue at risk</span><span className="stat-value">{money(d.totals.amount_at_risk, d.totals.currency)}</span>
                  <span className="stat-foot">{d.note}</span></div>
                <div className="card stat"><span className="stat-label">Last scan</span><span className="stat-value" style={{ fontSize: 18 }}>{dateTime(d.last_scan_at, timeZone)}</span></div>
              </div>
            )}
            <Card flush>
              {d.items.length === 0 ? <Empty title={status === "open" ? "Nothing at risk right now" : `No ${status} findings`} /> : (
                <div className="table-wrap"><table className="table">
                  <thead><tr><th>Finding</th><th>Kind</th><th className="num">At risk</th><th>Evidence</th><th>Detected</th><th /></tr></thead>
                  <tbody>{d.items.map((f) => (
                    <tr key={f.id}>
                      <td><b>{f.label}</b></td><td><StatusBadge value={f.status === "open" ? "overdue" : f.status} text={label(f.kind)} /></td>
                      <td className="num">{money(f.amount_at_risk, f.currency ?? d.totals.currency)}</td>
                      <td className="small muted">{Object.entries(f.evidence).filter(([k]) => k !== "resolution_note").map(([k, v]) => `${label(k)}: ${String(v)}`).join(" · ")}
                        {typeof f.evidence.resolution_note === "string" && <div><b>Note:</b> {f.evidence.resolution_note}</div>}</td>
                      <td>{dateTime(f.detected_at, timeZone)}</td>
                      <td className="num">{f.status === "open" && can("leakage.resolve") && (
                        <div className="row gap-sm end">
                          <button className="btn sm" onClick={() => { setActing({ f, resolution: "resolved" }); setNote(""); setError(null); }}>Resolve</button>
                          <button className="btn sm ghost" onClick={() => { setActing({ f, resolution: "dismissed" }); setNote(""); setError(null); }}>Dismiss</button>
                        </div>
                      )}</td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </Card>
          </>
        )}
      </Async>
      {acting && (
        <ConfirmDialog title={acting.resolution === "resolved" ? "Resolve this finding?" : "Dismiss this finding?"} message={acting.f.label}
          confirmLabel={acting.resolution === "resolved" ? "Resolve" : "Dismiss"} busy={busy} error={error}
          onCancel={() => setActing(null)} onConfirm={() => (acting.resolution === "dismissed" && !note.trim() ? setError(new ApiError(400, { code: "VALIDATION_FAILED",
            message: "Say why the finding is dismissed.", retryable: false, details: {} })) : void resolve())}>
          <Field label={acting.resolution === "dismissed" ? "Reason (required)" : "What was done (optional)"}>
            {(id) => <textarea id={id} className="textarea" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />}</Field>
        </ConfirmDialog>
      )}
    </>
  );
}
