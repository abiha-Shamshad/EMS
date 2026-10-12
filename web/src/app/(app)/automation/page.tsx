"use client";

import Link from "next/link";
import { useState } from "react";

import { Async, Card, Empty, Field, FormError, Modal, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { label } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Rule = { id: string; key: string; version: number; trigger: string; enabled: boolean; runs_7d: number; matched_7d: number; failed_7d: number };
type Sim = { matched: boolean; trace: { fact: string; op: string; value: unknown; actual: unknown; result: boolean }[]; actions: Record<string, unknown>[] };

const SAMPLE_FACTS: Record<string, Record<string, unknown>> = {
  "deal.stale": { "deal.days_since_activity": 15, "deal.stage": "proposal", "deal.amount": "5000.00", "deal.title": "Website rebuild" },
  "task.overdue": { "task.hours_overdue": 30, "task.billable": true, "task.status": "overdue", "project.billing_type": "hourly", "task.title": "Auth API" },
  "attendance.late": { "employee.minutes_late": 25, "employee.late_count_7d": 3, "employee.role": "employee", "employee.name": "Bilal Ahmed" },
  "invoice.overdue": { "invoice.days_overdue": 31, "invoice.outstanding": "6000.00", "client.status": "active", "invoice.number": "INV-2026-1031" },
  "leave.requested": { "leave.days": 3, "leave.kind": "annual", "employee.leave_balance": 11, "team.on_leave_count": 2, "employee.name": "Bilal Ahmed" },
  "prospect.scored": { "prospect.score": 85, "prospect.has_public_email": true, "prospect.country": "PK", "prospect.company_name": "BrightPixel" },
};

/** Screen 44 - automation dashboard and API usage (API-061), with the rule simulator (API-063). */
export default function AutomationPage() {
  const { can } = useSession();
  const rules = useApi<{ items: Rule[]; external_api_calls_7d: number }>(can("rules.manage") ? "/rules" : null);
  const [sim, setSim] = useState<Rule | null>(null);
  const [facts, setFacts] = useState("");
  const [result, setResult] = useState<Sim | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("rules.manage")) return <NoAccess message="Only leadership can manage automations." />;

  async function simulate() {
    if (!sim) return;
    setError(null);
    setResult(null);
    let parsed: unknown;
    try {
      parsed = JSON.parse(facts);
    } catch {
      setError(new ApiError(400, { code: "VALIDATION_FAILED", message: "Facts must be valid JSON.", retryable: false, details: {} }));
      return;
    }
    try {
      setResult(await post<Sim>(`/rules/${sim.id}/simulate`, { facts: parsed }));
    } catch (e) {
      setError(e as ApiError);
    }
  }

  return (
    <>
      <PageHeader title="Automations" subtitle="Rules run inside EMS on company events. No code, no external AI or API calls."
        actions={<><Link className="btn ghost" href="/automation/logs">Execution logs</Link><Link className="btn" href="/automation/new">New rule</Link></>} />
      <Async state={rules}>
        {(r) => {
          const runs = r.items.reduce((n, x) => n + x.runs_7d, 0);
          const matched = r.items.reduce((n, x) => n + x.matched_7d, 0);
          const failed = r.items.reduce((n, x) => n + x.failed_7d, 0);
          return (
            <>
              <div className="grid grid-4">
                <div className="card stat"><span className="stat-label">Active rules</span><span className="stat-value">{r.items.filter((x) => x.enabled).length}</span></div>
                <div className="card stat"><span className="stat-label">Runs (7 days)</span><span className="stat-value">{runs}</span><span className="stat-foot">{matched} matched</span></div>
                <Link href="/automation/logs" className="card stat" style={{ color: "inherit", textDecoration: "none" }}><span className="stat-label">Failed actions (7 days)</span>
                  <span className="stat-value" style={{ color: failed ? "var(--danger)" : undefined }}>{failed}</span></Link>
                <div className="card stat"><span className="stat-label">External API calls (7 days)</span><span className="stat-value">{r.external_api_calls_7d}</span>
                  <span className="stat-foot">Rules run inside EMS at no per-call cost</span></div>
              </div>
              <Card title="Rules" subtitle="The newest version of each rule runs" flush>
                {r.items.length === 0 ? <Empty title="No rules yet">Starter rules are added for every new company.</Empty> : (
                  <div className="table-wrap"><table className="table">
                    <thead><tr><th>Rule</th><th>Trigger</th><th className="num">Version</th><th className="num">Runs 7d</th><th className="num">Matched</th><th className="num">Failed</th><th /></tr></thead>
                    <tbody>{r.items.map((x) => (
                      <tr key={x.id}>
                        <td><b className="mono">{x.key}</b> {!x.enabled && <StatusBadge value="disabled" />}</td><td><span className="badge primary">{x.trigger}</span></td>
                        <td className="num">v{x.version}</td><td className="num">{x.runs_7d}</td><td className="num">{x.matched_7d}</td>
                        <td className="num">{x.failed_7d ? <span className="badge danger">{x.failed_7d}</span> : 0}</td>
                        <td className="num"><div className="row gap-sm end">
                          <button className="btn sm ghost" onClick={() => { setSim(x); setFacts(JSON.stringify(SAMPLE_FACTS[x.trigger] ?? {}, null, 2)); setResult(null); setError(null); }}>Simulate</button>
                          <Link className="btn sm ghost" href={`/automation/logs?rule_id=${x.id}`}>Runs</Link>
                        </div></td>
                      </tr>
                    ))}</tbody>
                  </table></div>
                )}
              </Card>
            </>
          );
        }}
      </Async>
      {sim && (
        <Modal wide title={`Simulate ${sim.key}`} subtitle={`Trigger ${sim.trigger}. Runs the rule against these facts with no side effects.`} onClose={() => setSim(null)}
          footer={<><button className="btn ghost" onClick={() => setSim(null)}>Close</button><button className="btn" onClick={() => void simulate()}>Run simulation</button></>}>
          <Field label="Facts (JSON)">{(id) => <textarea id={id} className="textarea mono" style={{ minHeight: 160 }} value={facts} onChange={(e) => setFacts(e.target.value)} />}</Field>
          <FormError error={error} />
          {result && (
            <div className="stack-sm">
              <span className={`badge ${result.matched ? "success" : ""}`}>{result.matched ? "Matched" : "Not matched"}</span>
              <div className="table-wrap card flush"><table className="table">
                <thead><tr><th>Fact</th><th>Condition</th><th>Actual</th><th>Result</th></tr></thead>
                <tbody>{result.trace.map((t, i) => (
                  <tr key={i}><td className="mono">{t.fact}</td><td className="mono">{t.op} {JSON.stringify(t.value)}</td><td className="mono">{JSON.stringify(t.actual)}</td>
                    <td>{t.result ? <span className="badge success">true</span> : <span className="badge">false</span>}</td></tr>
                ))}</tbody>
              </table></div>
              {result.actions.length > 0 && <div><b>Would run:</b> {result.actions.map((a) => label(String(a.action))).join(", ")}
                <pre className="code" style={{ marginTop: 8 }}>{JSON.stringify(result.actions, null, 2)}</pre></div>}
            </div>
          )}
        </Modal>
      )}
    </>
  );
}
