"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { Icon } from "@/components/icons";
import { Field, FormError } from "@/components/ui";
import { ApiError, post, selectOrg } from "@/lib/api";

type LoginResult = { organizations: { id: string; name: string; role: string }[]; redirect: string };

/** Screen 01 - sign in (API-003) and Google sign-in (API-007). */
function LoginForm() {
  const router = useRouter();
  const params = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const next = params.get("next");
  const safeNext = next && next.startsWith("/") && !next.startsWith("//") ? next : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await post<LoginResult>("/auth/login", { email, password, remember });
      if (res.organizations.length === 1) selectOrg(res.organizations[0]!.id);
      else selectOrg(null);
      try {
        window.sessionStorage.setItem("ems_orgs", JSON.stringify(res.organizations));   // names for the company picker
      } catch {
        // the picker falls back to company IDs
      }
      router.replace(res.organizations.length === 1 && safeNext ? safeNext : res.redirect);
    } catch (err) {
      setError(err as ApiError);
      setBusy(false);
    }
  }

  async function google() {
    setError(null);
    const url = `/api/v1/auth/google/start${safeNext ? `?return_to=${encodeURIComponent(safeNext)}` : ""}`;
    const res = await fetch(url, { redirect: "manual", credentials: "same-origin" }).catch(() => null);
    if (res && res.type !== "opaqueredirect" && !res.ok) {
      const body = await res.json().catch(() => null);
      setError(new ApiError(res.status, body?.error ?? { code: "INTERNAL_ERROR", message: "Google sign-in failed.", retryable: true, details: {} }));
      return;
    }
    window.location.assign(new URL(url, window.location.origin).href);       // an API redirect to Google, not a page route
  }

  const oauthError = params.get("error");
  return (
    <AuthLayout>
      <AuthHeading eyebrow="Your workspace awaits" title="Sign in to EMS">Use your work account to continue to your company workspace.</AuthHeading>
      {oauthError && <div className="alert error">Google sign-in did not complete. Try again or use your password.</div>}
      <form className="stack" onSubmit={submit} noValidate>
        <Field label="Work email" error={error?.fields.email}>
          {(id, invalid) => <input id={id} className="input" type="email" autoComplete="email" placeholder="name@company.com" required
            value={email} onChange={(e) => setEmail(e.target.value)} aria-invalid={invalid} />}
        </Field>
        <Field label="Password" error={error?.fields.password}>
          {(id, invalid) => (
            <div style={{ position: "relative" }}>
              <input id={id} className="input" type={show ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password"
                required value={password} onChange={(e) => setPassword(e.target.value)} aria-invalid={invalid} style={{ paddingRight: 44 }} />
              <button type="button" className="link-btn" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide password" : "Show password"}
                style={{ position: "absolute", right: 12, top: 11, color: "var(--muted)" }}><Icon name="eye" /></button>
            </div>
          )}
        </Field>
        <div className="row between">
          <label className="check"><input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} /> Keep me signed in</label>
          <Link href="/forgot-password" style={{ fontWeight: 600 }}>Forgot password?</Link>
        </div>
        <FormError error={error?.code === "VALIDATION_FAILED" ? null : error} />
        <button className="btn dark block" disabled={busy || !email || !password}>{busy ? "Signing in…" : <>Sign in <Icon name="arrow" /></>}</button>
      </form>
      <div className="divider">OR CONTINUE WITH</div>
      <button className="btn ghost block" onClick={() => void google()}>Continue with Google</button>
      <p className="muted" style={{ textAlign: "center" }}>New to EMS? <Link href="/signup" style={{ fontWeight: 600 }}>Create a company account</Link></p>
      <p className="muted small row gap-sm" style={{ justifyContent: "center" }}><Icon name="shield" size={14} /> Secure access for your organization</p>
    </AuthLayout>
  );
}

export default function LoginPage() {
  return <Suspense><LoginForm /></Suspense>;
}
