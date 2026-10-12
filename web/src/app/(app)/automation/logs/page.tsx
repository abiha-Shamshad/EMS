"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";

import { Card, Empty, ErrorState, Loading, LoadMore, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, get } from "@/lib/api";
import { dateTime, label } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Run = { id: string; rule: string; event: string; outcome: string; actions: string[]; ran_at: string };
type RunPage = { items: Run[]; next_cursor: string | null };

/** Screen 45 - workflow execution logs and alerts (API-064). Failed actions are rolled back and listed as alerts. */
function Logs() {
  const params = useSearchParams();
  const { can, timeZone } = useSession();
  const ruleId = params.get("rule_id");
  const [outcome, setOutcome] = useState("");
  const runs = useApi<RunPage>(can("rules.manage") ? "/rule-runs" : null, { rule_id: ruleId, outcome: outcome || null, limit: 50 });
  const failed = useApi<RunPage>(can("rules.manage") ? "/rule-runs" : null, { outcome: "action_failed", limit: 5 });
  const [extra, setExtra] = useState<Run[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("rules.manage")) return <NoAccess message="Only leadership can view automation logs." />;

  const next = cursor === undefined ? runs.data?.next_cursor : cursor;
  async function more() {
    try {
      const p = await get<RunPage>("/rule-runs", { rule_id: ruleId, outcome: outcome || null, limit: 50, cursor: next });
      setExtra((e) => [...e, ...p.items]);
      setCursor(p.next_cursor);
    } catch (e) {
      setError(e as ApiError);
    }
  }
  const items = [...(runs.data?.items ?? []), ...extra];

  return (
    <>
      <PageHeader title="Execution logs" subtitle={ruleId ? <>Runs of one rule · <Link href="/automation/logs">show all</Link></> : "Every rule run, once per rule and event"}
        actions={<select className="select" style={{ width: 170 }} value={outcome} onChange={(e) => { setOutcome(e.target.value); setExtra([]); setCursor(undefined); }} aria-label="Outcome">
          <option value="">All outcomes</option>{["matched", "not_matched", "action_failed", "skipped_loop"].map((o) => <option key={o} value={o}>{label(o)}</option>)}</select>} />
      {failed.data && failed.data.items.length > 0 && (
        <div className="alert error">
          <b>Alerts:</b> {failed.data.items.length} recent run(s) had a failed action, so none of that rule&apos;s actions were applied
          ({failed.data.items.map((f) => f.rule).join(", ")}).
        </div>
      )}
      <Card flush>
        {runs.error && !runs.data ? <div style={{ padding: 20 }}><ErrorState error={runs.error} retry={runs.reload} /></div> : !runs.data ? <Loading /> :
          items.length === 0 ? <Empty title="No runs yet">Rules run when their trigger event happens.</Empty> : (
            <div className="table-wrap"><table className="table">
              <thead><tr><th>When</th><th>Rule</th><th>Trigger</th><th>Outcome</th><th>Actions</th></tr></thead>
              <tbody>{items.map((r) => (
                <tr key={r.id}><td>{dateTime(r.ran_at, timeZone)}</td><td className="mono">{r.rule}</td><td><span className="badge primary">{r.event}</span></td>
                  <td><StatusBadge value={r.outcome} /></td><td>{r.actions.length ? r.actions.map(label).join(", ") : <span className="muted">—</span>}</td></tr>
              ))}</tbody>
            </table></div>
          )}
        {error && <div style={{ padding: 12 }}><ErrorState error={error} /></div>}
        <LoadMore cursor={next} onMore={() => void more()} />
      </Card>
    </>
  );
}

export default function LogsPage() {
  return <Suspense><Logs /></Suspense>;
}
