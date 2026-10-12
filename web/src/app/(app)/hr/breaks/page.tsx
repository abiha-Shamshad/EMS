"use client";

import { useState } from "react";

import { Async, Card, Empty, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { dateTime, label, minutes, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type BreakRow = { id: string; user_id: string; name: string; kind: string; status: string; requested_minutes: number; minutes: number | null;
  started_at: string | null; created_at: string; can_decide: boolean };

function shift(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Screen 29 - break log, and decisions on breaks above the daily allowance (API-022). */
export default function BreakLogPage() {
  const toast = useToast();
  const { timeZone, can } = useSession();
  const end = today(timeZone);
  const [from, setFrom] = useState(shift(end, -6));
  const [to, setTo] = useState(end);
  const log = useApi<{ items: BreakRow[] }>("/room/breaks", { from, to });
  const [busy, setBusy] = useState<string | null>(null);

  async function decide(b: BreakRow, decision: "approved" | "rejected") {
    setBusy(b.id);
    try {
      await post(`/room/breaks/${b.id}/decision`, { decision });
      toast(decision === "approved" ? `${b.name}'s break started` : `${b.name}'s break request was rejected`);
      log.reload();
    } catch (e) {
      toast((e as ApiError).message, "error");
    } finally {
      setBusy(null);
    }
  }

  return (
    <>
      <PageHeader title="Break log" subtitle={can("leave.decide") ? "Breaks above the daily allowance wait for a decision here." : "Your breaks"} actions={<>
        <input className="input" type="date" style={{ width: 160 }} value={from} max={to} onChange={(e) => setFrom(e.target.value)} aria-label="From" />
        <input className="input" type="date" style={{ width: 160 }} value={to} min={from} max={end} onChange={(e) => setTo(e.target.value)} aria-label="To" />
      </>} />
      <Card flush>
        <Async state={log}>
          {(l) => l.items.length === 0 ? <Empty title="No breaks in this period" /> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Employee</th><th>Kind</th><th>Status</th><th className="num">Requested</th><th className="num">Taken</th><th>Requested at</th><th /></tr></thead>
                <tbody>{l.items.map((b) => (
                  <tr key={b.id}>
                    <td>{b.name}</td><td>{label(b.kind)}</td><td><StatusBadge value={b.status} /></td>
                    <td className="num">{b.requested_minutes} min</td><td className="num">{b.minutes !== null ? minutes(b.minutes) : "—"}</td>
                    <td>{dateTime(b.created_at, timeZone)}</td>
                    <td className="num">{b.can_decide && (
                      <div className="row gap-sm end">
                        <button className="btn sm" disabled={busy === b.id} onClick={() => void decide(b, "approved")}>Approve</button>
                        <button className="btn sm ghost" disabled={busy === b.id} onClick={() => void decide(b, "rejected")}>Reject</button>
                      </div>
                    )}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        </Async>
      </Card>
    </>
  );
}
