"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { Async, Card, Empty, Field, FormError, PageHeader, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { date, label, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { LeaveRow } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Created = { request_id: string; days: number; approver: string; balance_after_approval: Record<string, number> };

/** Screen 27 - request leave and see my requests (API-031/032). */
export default function LeavePage() {
  const toast = useToast();
  const { can, timeZone } = useSession();
  const mine = useApi<{ items: LeaveRow[] }>("/leave-requests", { scope: "mine" });
  const [f, setF] = useState({ kind: "annual", start_date: today(timeZone), end_date: today(timeZone), reason: "" });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key, setKey] = useState(newIdempotencyKey);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await post<Created>("/leave-requests", { ...f, reason: f.reason || null }, { idempotencyKey: key });
      toast(`Request for ${res.days} day(s) sent to ${res.approver}`);
      setKey(newIdempotencyKey());
      setF((cur) => ({ ...cur, reason: "" }));
      mine.reload();
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }
  const fe = error?.fields ?? {};

  return (
    <>
      <PageHeader title="Leave" subtitle="Working days only; balances come from the published leave policy."
        actions={can("leave.decide") && <Link className="btn ghost" href="/leave/approvals">Approvals</Link>} />
      <div className="grid grid-3">
        <Card title="Request leave">
          <form className="stack" onSubmit={submit} noValidate>
            <Field label="Kind" error={fe.kind}>
              {(id) => <select id={id} className="select" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>
                {["annual", "sick", "casual", "unpaid"].map((k) => <option key={k} value={k}>{label(k)}</option>)}</select>}
            </Field>
            <Field label="First day" error={fe.start_date}>
              {(id, inv) => <input id={id} className="input" type="date" value={f.start_date} onChange={(e) => setF({ ...f, start_date: e.target.value })} aria-invalid={inv} />}
            </Field>
            <Field label="Last day" error={fe.end_date}>
              {(id, inv) => <input id={id} className="input" type="date" min={f.start_date} value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} aria-invalid={inv} />}
            </Field>
            <Field label="Reason (optional)" error={fe.reason}>
              {(id, inv) => <textarea id={id} className="textarea" maxLength={500} value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} aria-invalid={inv} />}
            </Field>
            <FormError error={error && !Object.keys(fe).length ? error : null} />
            <button className="btn" disabled={busy}>{busy ? "Sending…" : "Send request"}</button>
          </form>
        </Card>
        <Card title="My requests" className="span-2" flush>
          <Async state={mine}>
            {(m) => m.items.length === 0 ? <Empty title="No leave requests yet" /> : (
              <div className="table-wrap">
                <table className="table">
                  <thead><tr><th>Kind</th><th>Dates</th><th className="num">Days</th><th>Status</th></tr></thead>
                  <tbody>{m.items.map((r) => (
                    <tr key={r.request_id}><td>{label(r.kind)}</td><td>{date(r.start_date)} – {date(r.end_date)}</td><td className="num">{r.days}</td><td><StatusBadge value={r.status} /></td></tr>
                  ))}</tbody>
                </table>
              </div>
            )}
          </Async>
        </Card>
      </div>
    </>
  );
}
