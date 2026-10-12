"use client";

import { useState, type FormEvent } from "react";

import { Icon } from "@/components/icons";
import { Field, FormError, StatusBadge, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { label } from "@/lib/format";

type Result = { email: string; status: "invited" | "already_member" | "already_invited"; invite_link?: string; expires_at?: string };
export type InviteResponse = { results: Result[]; email_delivery: string; org_setup_state: string };

const ROLES = ["employee", "manager", "hr", "cto", "cfo", "coo"];

/** Invite rows (API-011). Email is not configured in Release 1 (INT-003), so each invite gets a link to share (AUD-03). */
export function InviteForm({ isCeo, onDone }: { isCeo: boolean; onDone?: (r: InviteResponse) => void }) {
  const toast = useToast();
  const roles = isCeo ? ROLES : ROLES.filter((r) => !["cto", "cfo", "coo"].includes(r));    // only the CEO grants leadership roles
  const [rows, setRows] = useState([{ email: "", role: "employee" }]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<InviteResponse | null>(null);
  const [key, setKey] = useState(newIdempotencyKey);
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const invites = rows.filter((r) => r.email.trim());
      const res = await post<InviteResponse>("/invitations", { invites, ...(message ? { message } : {}) }, { idempotencyKey: key });
      setResult(res);
      setKey(newIdempotencyKey());
      onDone?.(res);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  const copy = (link: string) => navigator.clipboard.writeText(link).then(() => toast("Invite link copied"), () => toast("Copy failed", "error"));

  if (result) {
    return (
      <div className="stack">
        {result.email_delivery === "not_configured" && (
          <div className="alert info">Email isn&apos;t set up yet, so nothing was sent. Share each link with the person directly; links expire in 7 days.</div>
        )}
        <div className="table-wrap card flush">
          <table className="table">
            <thead><tr><th>Email</th><th>Status</th><th>Invite link</th></tr></thead>
            <tbody>
              {result.results.map((r) => (
                <tr key={r.email}>
                  <td>{r.email}</td>
                  <td><StatusBadge value={r.status} /></td>
                  <td>{r.invite_link ? <button className="btn sm ghost" onClick={() => void copy(r.invite_link!)}><Icon name="copy" size={14} /> Copy link</button>
                    : <span className="muted small">{r.status === "already_member" ? "Already in the company" : "Invitation still pending"}</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="row end"><button className="btn ghost" onClick={() => { setResult(null); setRows([{ email: "", role: "employee" }]); }}>Invite more people</button></div>
      </div>
    );
  }

  return (
    <form className="stack" onSubmit={submit} noValidate>
      {rows.map((r, i) => (
        <div className="row gap" key={i} style={{ alignItems: "flex-end" }}>
          <Field label={i === 0 ? "Email address" : ""} error={fe[`invites[${i}].email`]} className="grow">
            {(id, inv) => <input id={id} className="input" type="email" placeholder="teammate@company.com" value={r.email} aria-invalid={inv}
              onChange={(e) => setRows((cur) => cur.map((x, j) => j === i ? { ...x, email: e.target.value } : x))} />}
          </Field>
          <Field label={i === 0 ? "Role" : ""} error={fe[`invites[${i}].role`]}>
            {(id, inv) => <select id={id} className="select" value={r.role} aria-invalid={inv} style={{ width: 150 }}
              onChange={(e) => setRows((cur) => cur.map((x, j) => j === i ? { ...x, role: e.target.value } : x))}>
              {roles.map((x) => <option key={x} value={x}>{label(x)}</option>)}</select>}
          </Field>
          {rows.length > 1 && <button type="button" className="icon-btn" aria-label="Remove row"
            onClick={() => setRows((cur) => cur.filter((_, j) => j !== i))}><Icon name="close" size={16} /></button>}
        </div>
      ))}
      {rows.length < 20 && <button type="button" className="link-btn" onClick={() => setRows((cur) => [...cur, { email: "", role: "employee" }])}>+ Add another</button>}
      <Field label="Personal message (optional)" hint={`${message.length}/300`} error={fe.message}>
        {(id, inv) => <textarea id={id} className="textarea" maxLength={300} value={message} onChange={(e) => setMessage(e.target.value)} aria-invalid={inv}
          placeholder="Hi! Join our company workspace on EMS." />}
      </Field>
      <FormError error={error && !Object.keys(fe).length ? error : null} />
      <div className="row end"><button className="btn" disabled={busy || !rows.some((r) => r.email.trim())}>{busy ? "Creating…" : "Create invitations"}</button></div>
    </form>
  );
}
