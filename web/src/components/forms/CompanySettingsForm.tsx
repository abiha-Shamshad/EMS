"use client";

import { useMemo, useState, type FormEvent } from "react";

import { Field, FormError } from "@/components/ui";
import { ApiError, patch } from "@/lib/api";

export type Org = {
  id: string; name: string; slug: string; time_zone: string; country: string; industry: string | null; size_band: string | null;
  setup_state: string; version: number; work_hours: { days: string[]; start: string; end: string; late_grace_minutes: number };
  base_currency: string; live_view_enabled: boolean; room_policy_version: number; daily_break_allowance_minutes: number;
};

const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
const SIZES = ["1-10", "11-50", "51-200", "201-500", "500+"];

/** Company details and working hours (API-010). Used by onboarding step 2 and by Company settings. */
export function CompanySettingsForm({ org, submitLabel, onSaved, onSkip }: {
  org: Org; submitLabel: string; onSaved: (next: { setup_state: string; version: number; next_step: string }) => void; onSkip?: () => void;
}) {
  const zones = useMemo(() => (typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [org.time_zone]), [org.time_zone]);
  const [industry, setIndustry] = useState(org.industry ?? "");
  const [size, setSize] = useState(org.size_band ?? "");
  const [tz, setTz] = useState(org.time_zone);
  const [days, setDays] = useState<string[]>(org.work_hours.days);
  const [start, setStart] = useState(org.work_hours.start);
  const [end, setEnd] = useState(org.work_hours.end);
  const [grace, setGrace] = useState(org.work_hours.late_grace_minutes);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body: Record<string, unknown> = { expected_version: org.version, time_zone: tz,
        work_hours: { days, start, end, late_grace_minutes: Number(grace) } };
      if (industry) body.industry = industry;
      if (size) body.size_band = size;
      onSaved(await patch("/org", body));
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit} noValidate>
      <div className="form-grid">
        <Field label="Company name" hint="Set when the account was created">
          {(id) => <input id={id} className="input" value={org.name} disabled />}
        </Field>
        <Field label="Industry" error={fe.industry}>
          {(id, inv) => <input id={id} className="input" placeholder="e.g. Software services" value={industry} onChange={(e) => setIndustry(e.target.value)} aria-invalid={inv} />}
        </Field>
        <Field label="Company size" error={fe.size_band}>
          {(id, inv) => <select id={id} className="select" value={size} onChange={(e) => setSize(e.target.value)} aria-invalid={inv}>
            <option value="">Choose…</option>{SIZES.map((s) => <option key={s} value={s}>{s} people</option>)}</select>}
        </Field>
        <Field label="Time zone" error={fe.time_zone}>
          {(id, inv) => <select id={id} className="select" value={tz} onChange={(e) => setTz(e.target.value)} aria-invalid={inv}>
            {zones.map((z) => <option key={z}>{z}</option>)}</select>}
        </Field>
        <div className="field full">
          <span>Working days</span>
          <div className="row gap wrap">
            {DAYS.map((d) => (
              <label key={d} className="check">
                <input type="checkbox" checked={days.includes(d)} onChange={(e) => setDays((cur) => e.target.checked ? [...cur, d] : cur.filter((x) => x !== d))} />
                {d[0]!.toUpperCase() + d.slice(1)}
              </label>
            ))}
          </div>
          {fe.work_hours && <span className="err">{fe.work_hours}</span>}
        </div>
        <Field label="Work starts" error={fe["work_hours.start"]}>
          {(id, inv) => <input id={id} className="input" type="time" value={start} onChange={(e) => setStart(e.target.value)} aria-invalid={inv} />}
        </Field>
        <Field label="Work ends" error={fe["work_hours.end"]}>
          {(id, inv) => <input id={id} className="input" type="time" value={end} onChange={(e) => setEnd(e.target.value)} aria-invalid={inv} />}
        </Field>
        <Field label="Late grace (minutes)" error={fe["work_hours.late_grace_minutes"]} hint="Check-ins within this window are not late">
          {(id, inv) => <input id={id} className="input" type="number" min={0} max={120} value={grace} onChange={(e) => setGrace(Number(e.target.value))} aria-invalid={inv} />}
        </Field>
      </div>
      <FormError error={error && !Object.keys(fe).length ? error : null} />
      <div className="row gap end">
        {onSkip && <button type="button" className="btn ghost" onClick={onSkip}>Skip for now</button>}
        <button className="btn" disabled={busy || days.length === 0}>{busy ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}
