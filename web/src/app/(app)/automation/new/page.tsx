"use client";

import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import { Card, Field, FormError, NoAccess, PageHeader, useToast } from "@/components/ui";
import { ApiError, newIdempotencyKey, post } from "@/lib/api";
import { useSession } from "@/lib/session";

// Facts each trigger offers and who its actions can address (mirrors engine/rules.py and app/rules/service.py; the API re-validates).
const TRIGGERS: Record<string, { facts: string[]; recipients: string[]; example: object }> = {
  "deal.stale": { facts: ["deal.days_since_activity", "deal.stage", "deal.amount", "deal.owner_role"], recipients: ["owner"],
    example: { trigger: "deal.stale", when: { all: [{ fact: "deal.days_since_activity", op: "gte", value: 14 }] },
      then: [{ action: "notify", to: "owner", template: "deal_stale" }, { action: "create_task", assign: "owner", title: "Follow up: {deal.title}", due_in_hours: 24 }] } },
  "task.overdue": { facts: ["task.hours_overdue", "task.status", "task.billable", "project.billing_type"], recipients: ["project_owner", "employee"],
    example: { trigger: "task.overdue", when: { all: [{ fact: "task.billable", op: "eq", value: true }, { fact: "task.hours_overdue", op: "gte", value: 24 }] },
      then: [{ action: "notify", to: "project_owner", template: "task_overdue" }] } },
  "attendance.late": { facts: ["employee.minutes_late", "employee.late_count_7d", "employee.role", "employee.department", "day.is_holiday"], recipients: ["employee", "manager"],
    example: { trigger: "attendance.late", when: { all: [{ fact: "employee.late_count_7d", op: "gte", value: 3 }] }, then: [{ action: "notify", to: "hr", template: "late_three_times" }] } },
  "invoice.overdue": { facts: ["invoice.days_overdue", "invoice.outstanding", "client.status"], recipients: ["project_owner"],
    example: { trigger: "invoice.overdue", when: { all: [{ fact: "invoice.days_overdue", op: "gte", value: 30 }] }, then: [{ action: "set_stage_flag", flag: "at_risk" }] } },
  "leave.requested": { facts: ["leave.days", "leave.kind", "employee.leave_balance", "team.on_leave_count"], recipients: ["employee", "manager", "approver"],
    example: { trigger: "leave.requested", when: { all: [{ fact: "team.on_leave_count", op: "gte", value: 2 }] }, then: [{ action: "escalate", to: "ceo", template: "leave_team_overlap" }] } },
  "prospect.scored": { facts: ["prospect.score", "prospect.has_public_email", "prospect.country"], recipients: ["hunt_owner"],
    example: { trigger: "prospect.scored", when: { all: [{ fact: "prospect.score", op: "gte", value: 80 }] }, then: [{ action: "notify", to: "hunt_owner", template: "prospect_high_score" }] } },
};

/** Create a rule or a new version of one (API-062). Definitions are JSON: trigger, when (all/any, depth 3, 20 conditions), then (up to 5 actions). */
export default function NewRulePage() {
  const router = useRouter();
  const toast = useToast();
  const { can } = useSession();
  const [trigger, setTrigger] = useState("deal.stale");
  const [key, setKey] = useState("");
  const [json, setJson] = useState(JSON.stringify(TRIGGERS["deal.stale"]!.example, null, 2));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [idem] = useState(newIdempotencyKey);
  if (!can("rules.manage")) return <NoAccess message="Only leadership can manage automations." />;
  const t = TRIGGERS[trigger]!;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    let definition: unknown;
    try {
      definition = JSON.parse(json);
    } catch {
      setError(new ApiError(400, { code: "VALIDATION_FAILED", message: "The definition must be valid JSON.", retryable: false, details: {} }));
      return;
    }
    setBusy(true);
    try {
      const r = await post<{ key: string; version: number }>("/rules", { key, definition }, { idempotencyKey: idem });
      toast(`Rule ${r.key} v${r.version} saved`);
      router.push("/automation");
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  return (
    <>
      <PageHeader title="New rule" subtitle="Saving an existing key creates its next version; older versions stop running." />
      <div className="grid grid-3">
        <Card title="Definition" className="span-2">
          <form className="stack" onSubmit={submit} noValidate>
            <div className="form-grid">
              <Field label="Key" error={error?.fields.key} hint="3-60 lowercase letters, digits or _">
                {(id, inv) => <input id={id} className="input mono" value={key} onChange={(e) => setKey(e.target.value.toLowerCase())} aria-invalid={inv} placeholder="stale_deal_nudge" />}</Field>
              <Field label="Start from trigger">
                {(id) => <select id={id} className="select" value={trigger} onChange={(e) => { setTrigger(e.target.value); setJson(JSON.stringify(TRIGGERS[e.target.value]!.example, null, 2)); }}>
                  {Object.keys(TRIGGERS).map((k) => <option key={k}>{k}</option>)}</select>}</Field>
            </div>
            <Field label="Rule JSON" error={error?.code === "RULE_INVALID" ? `${error.message} (${String(error.details.reason)})` : undefined}>
              {(id, inv) => <textarea id={id} className="textarea mono" style={{ minHeight: 320 }} spellCheck={false} value={json} onChange={(e) => setJson(e.target.value)} aria-invalid={inv} />}</Field>
            <FormError error={error && error.code !== "RULE_INVALID" && !error.fields.key ? error : null} />
            <div className="row end"><button className="btn" disabled={busy || key.length < 3}>{busy ? "Saving…" : "Save rule"}</button></div>
          </form>
        </Card>
        <Card title="Reference">
          <div className="stack-sm small">
            <b>Facts for {trigger}</b>
            <div className="row gap-sm wrap">{t.facts.map((f) => <span key={f} className="badge mono">{f}</span>)}</div>
            <b>Operators</b><span className="mono">eq neq gt gte lt lte in not_in contains is_empty</span>
            <b>Actions</b><span className="mono">notify escalate create_task assign_owner set_stage_flag create_finding</span>
            <b>Who actions can address</b>
            <span className="mono">{[...t.recipients, "hr", "ceo", "coo", "cfo", "leadership"].join(" ")}</span>
            <b>Notification templates</b>
            <span className="mono">deal_stale task_overdue late_three_times invoice_overdue leave_team_overlap prospect_high_score</span>
            <p className="muted">Text fields can use {"{fact.name}"} placeholders. No code, regular expressions or URLs are accepted.</p>
          </div>
        </Card>
      </div>
    </>
  );
}
