"use client";

import { useState } from "react";

import { Async, Card, ConfirmDialog, Empty, Field, NoAccess, PageHeader, StatusBadge, Tabs, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { date, label } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { LeaveRow } from "@/lib/types";
import { useApi } from "@/lib/useApi";

/** Screen 28 - leave approval (API-032 scope=to_decide, API-033). Nobody decides their own leave. */
export default function LeaveApprovalsPage() {
  const toast = useToast();
  const { can } = useSession();
  const [status, setStatus] = useState<"pending" | "approved" | "rejected">("pending");
  const list = useApi<{ items: LeaveRow[] }>(can("leave.decide") ? "/leave-requests" : null, { scope: "to_decide", status });
  const [deciding, setDeciding] = useState<{ row: LeaveRow; decision: "approved" | "rejected" } | null>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("leave.decide")) return <NoAccess message="Only the CEO, HR and managers decide leave." />;

  async function decide() {
    if (!deciding) return;
    setBusy(true);
    setError(null);
    try {
      await post(`/leave-requests/${deciding.row.request_id}/decision`, { expected_version: deciding.row.version, decision: deciding.decision, ...(note ? { note } : {}) });
      toast(`Leave ${deciding.decision} for ${deciding.row.employee}`);
      setDeciding(null);
      list.reload();
    } catch (e) {
      setError(e as ApiError);
      if ((e as ApiError).code === "VERSION_CONFLICT" || (e as ApiError).code === "ALREADY_DECIDED") list.reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Leave approvals" subtitle="Requests routed to you: your team, or the company for HR and the CEO" />
      <Tabs value={status} onChange={setStatus} options={[{ value: "pending", label: "Waiting" }, { value: "approved", label: "Approved" }, { value: "rejected", label: "Rejected" }]} />
      <Card flush>
        <Async state={list}>
          {(l) => l.items.length === 0 ? <Empty title={status === "pending" ? "Nothing waiting for you" : "No requests"} /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Employee</th><th>Kind</th><th>Dates</th><th className="num">Days</th><th>Team also away</th><th>Status</th><th /></tr></thead>
                <tbody>{l.items.map((r) => (
                  <tr key={r.request_id}>
                    <td><b>{r.employee}</b></td><td>{label(r.kind)}</td><td>{date(r.start_date)} – {date(r.end_date)}</td><td className="num">{r.days}</td>
                    <td>{r.team_on_leave_same_days > 0 ? <span className="badge warning">{r.team_on_leave_same_days} teammate(s)</span> : <span className="muted">None</span>}</td>
                    <td><StatusBadge value={r.status} /></td>
                    <td className="num">{r.status === "pending" && (
                      <div className="row gap-sm end">
                        <button className="btn sm" onClick={() => { setDeciding({ row: r, decision: "approved" }); setNote(""); setError(null); }}>Approve</button>
                        <button className="btn sm ghost" onClick={() => { setDeciding({ row: r, decision: "rejected" }); setNote(""); setError(null); }}>Reject</button>
                      </div>
                    )}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Async>
      </Card>
      {deciding && (
        <ConfirmDialog title={`${deciding.decision === "approved" ? "Approve" : "Reject"} ${deciding.row.employee}'s leave?`}
          message={`${label(deciding.row.kind)} leave, ${date(deciding.row.start_date)} – ${date(deciding.row.end_date)} (${deciding.row.days} working days).`}
          confirmLabel={deciding.decision === "approved" ? "Approve" : "Reject"} danger={deciding.decision === "rejected"} busy={busy} error={error}
          onCancel={() => setDeciding(null)} onConfirm={() => void decide()}>
          <Field label="Note to the employee (optional)">
            {(id) => <textarea id={id} className="textarea" maxLength={500} value={note} onChange={(e) => setNote(e.target.value)} />}
          </Field>
        </ConfirmDialog>
      )}
    </>
  );
}
