"use client";

import { useState } from "react";

import { Async, Card, Field, FormError, Modal, PageHeader, useToast } from "@/components/ui";
import { ApiError, put } from "@/lib/api";
import { dateTime, label } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Policy = { topic: string; version: number; text: string; published_at: string };
const TOPICS = ["leave", "attendance", "breaks", "general", "monitoring"] as const;
type Topic = (typeof TOPICS)[number];
// Machine rules each topic can carry (validated again by the API).
const RULES: Record<Topic, { key: string; text: string; max: number }[]> = {
  leave: [{ key: "annual_days", text: "Annual days per year", max: 365 }, { key: "sick_days", text: "Sick days per year", max: 365 },
    { key: "casual_days", text: "Casual days per year", max: 365 }, { key: "unpaid_days", text: "Unpaid days per year", max: 365 }],
  attendance: [{ key: "late_grace_minutes", text: "Late grace (minutes)", max: 120 }, { key: "daily_break_allowance_minutes", text: "Daily break allowance (minutes)", max: 240 }],
  breaks: [{ key: "daily_break_allowance_minutes", text: "Daily break allowance (minutes)", max: 240 }],
  general: [],
  monitoring: [],
};

/** Screen 32 - company policies the HR Agent quotes, and their rules (API-036/037). Publishing creates a new version. */
export default function PoliciesPage() {
  const toast = useToast();
  const { me, can } = useSession();
  const canPublish = can("hr.manage") && me.active_org.role !== "manager";
  const list = useApi<{ items: Policy[] }>("/hr-agent/policies");
  const [edit, setEdit] = useState<Topic | null>(null);
  const [text, setText] = useState("");
  const [rules, setRules] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const current = (t: string) => list.data?.items.find((p) => p.topic === t);

  function open(t: Topic) {
    setEdit(t);
    setText(current(t)?.text ?? "");
    setRules({});
    setError(null);
  }

  async function publish() {
    if (!edit) return;
    setBusy(true);
    setError(null);
    try {
      const r = Object.fromEntries(Object.entries(rules).filter(([, v]) => v !== "").map(([k, v]) => [k, Number(v)]));
      const res = await put<{ version: number }>(`/hr-agent/policies/${edit}`, { expected_version: current(edit)?.version ?? 0, text, rules: r });
      toast(`${label(edit)} policy v${res.version} published`);
      setEdit(null);
      list.reload();
    } catch (e) {
      setError(e as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="Policies & rules" subtitle="The HR Agent quotes these word for word. Rules feed leave balances, lateness and break allowances." />
      <Async state={list}>
        {() => (
          <div className="grid grid-2">
            {TOPICS.map((t) => {
              const p = current(t);
              return (
                <Card key={t} title={`${label(t)} policy`} subtitle={p ? `Version ${p.version} · published ${dateTime(p.published_at)}` : "Not published yet"}
                  actions={canPublish && <button className="btn sm ghost" onClick={() => open(t)}>{p ? "Publish new version" : "Publish"}</button>}>
                  <p style={{ whiteSpace: "pre-wrap" }} className={p ? "" : "muted"}>{p?.text ?? "Nothing published. The HR Agent will say so when asked."}</p>
                  {t === "monitoring" && <p className="muted small" style={{ marginTop: 8 }}>Publishing a new monitoring notice asks every employee to consent again before their next screen share.</p>}
                </Card>
              );
            })}
          </div>
        )}
      </Async>
      {edit && (
        <Modal wide title={`Publish ${label(edit)} policy`} subtitle={`This becomes version ${(current(edit)?.version ?? 0) + 1}. Earlier versions are kept.`} onClose={() => setEdit(null)}
          footer={<><button className="btn ghost" onClick={() => setEdit(null)}>Cancel</button>
            <button className="btn" disabled={busy || text.trim().length < 10} onClick={() => void publish()}>{busy ? "Publishing…" : "Publish"}</button></>}>
          <Field label="Policy text" hint="10 to 5000 characters, shown to employees" error={error?.fields.text}>
            {(id, inv) => <textarea id={id} className="textarea" style={{ minHeight: 160 }} maxLength={5000} value={text} onChange={(e) => setText(e.target.value)} aria-invalid={inv} />}
          </Field>
          {RULES[edit].length > 0 && (
            <div className="form-grid">
              {RULES[edit].map((r) => (
                <Field key={r.key} label={r.text} error={error?.fields[`rules.${r.key}`]} hint="Leave empty to leave unchanged">
                  {(id, inv) => <input id={id} className="input" type="number" min={0} max={r.max} value={rules[r.key] ?? ""} aria-invalid={inv}
                    onChange={(e) => setRules((cur) => ({ ...cur, [r.key]: e.target.value }))} />}
                </Field>
              ))}
            </div>
          )}
          <FormError error={error && !Object.keys(error.fields).length ? error : null} />
        </Modal>
      )}
    </>
  );
}
