"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type FormEvent } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { Field, FormError } from "@/components/ui";
import { ApiError, newIdempotencyKey, post, selectOrg } from "@/lib/api";

type SignupResult = { org: { id: string } };

const slugify = (s: string) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 41);

/** Screen 02 - create the company and its CEO account (API-002). */
export default function SignupPage() {
  const router = useRouter();
  const browserZone = useMemo(() => Intl.DateTimeFormat().resolvedOptions().timeZone, []);
  const zones = useMemo(() => (typeof Intl.supportedValuesOf === "function" ? Intl.supportedValuesOf("timeZone") : [browserZone]), [browserZone]);
  const [f, setF] = useState({ company_name: "", company_slug: "", country: "PK", time_zone: browserZone, name: "", email: "", password: "" });
  const [slugTouched, setSlugTouched] = useState(false);
  const [terms, setTerms] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [key] = useState(newIdempotencyKey);                 // one key per form: a double submit replays, never duplicates

  const set = (k: keyof typeof f) => (v: string) => setF((s) => ({ ...s, [k]: v, ...(k === "company_name" && !slugTouched ? { company_slug: slugify(v) } : {}) }));
  const fe = error?.fields ?? {};

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await post<SignupResult>("/auth/signup", f, { idempotencyKey: key });
      selectOrg(res.org.id);
      router.replace("/setup/company");
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  const fieldErr = (k: string) => fe[k] ?? (error?.details.field === k ? error.message : undefined);
  return (
    <AuthLayout>
      <AuthHeading eyebrow="Step 1 of 3" title="Create your company account">You&apos;ll be the CEO of this workspace and can invite your team next.</AuthHeading>
      <form className="stack" onSubmit={submit} noValidate>
        <div className="form-grid">
          <Field label="Company name" error={fieldErr("company_name")} className="full">
            {(id, inv) => <input id={id} className="input" required value={f.company_name} onChange={(e) => set("company_name")(e.target.value)} aria-invalid={inv} />}
          </Field>
          <Field label="Company address" error={fieldErr("company_slug")} hint="Lowercase letters, numbers and dashes" className="full">
            {(id, inv) => <input id={id} className="input" required value={f.company_slug} aria-invalid={inv}
              onChange={(e) => { setSlugTouched(true); set("company_slug")(e.target.value.toLowerCase()); }} />}
          </Field>
          <Field label="Country (2-letter code)" error={fieldErr("country")}>
            {(id, inv) => <input id={id} className="input" maxLength={2} required value={f.country} aria-invalid={inv}
              onChange={(e) => set("country")(e.target.value.toUpperCase())} />}
          </Field>
          <Field label="Time zone" error={fieldErr("time_zone")}>
            {(id, inv) => <select id={id} className="select" value={f.time_zone} onChange={(e) => set("time_zone")(e.target.value)} aria-invalid={inv}>
              {zones.map((z) => <option key={z}>{z}</option>)}</select>}
          </Field>
          <Field label="Your name" error={fieldErr("name")} className="full">
            {(id, inv) => <input id={id} className="input" autoComplete="name" required value={f.name} onChange={(e) => set("name")(e.target.value)} aria-invalid={inv} />}
          </Field>
          <Field label="Work email" error={fieldErr("email")} className="full">
            {(id, inv) => <input id={id} className="input" type="email" autoComplete="email" required value={f.email} onChange={(e) => set("email")(e.target.value)} aria-invalid={inv} />}
          </Field>
          <Field label="Password" error={fieldErr("password")} hint="12 to 128 characters; common passwords are refused" className="full">
            {(id, inv) => <input id={id} className="input" type="password" autoComplete="new-password" required value={f.password}
              onChange={(e) => set("password")(e.target.value)} aria-invalid={inv} />}
          </Field>
        </div>
        <label className="check"><input type="checkbox" checked={terms} onChange={(e) => setTerms(e.target.checked)} /> I agree to the EMS terms and privacy policy</label>
        <FormError error={error && !Object.keys(fe).length && !error.details.field ? error : null} />
        <button className="btn dark block" disabled={busy || !terms}>{busy ? "Creating…" : "Create company account"}</button>
      </form>
      <p className="muted" style={{ textAlign: "center" }}>Already have an account? <Link href="/login" style={{ fontWeight: 600 }}>Sign in</Link></p>
    </AuthLayout>
  );
}
