"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { Field, FormError } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

/** Screen 03 - request a reset link (API-005). While email is not configured (INT-003) no link is sent, and the page says so. */
export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [result, setResult] = useState<{ email_delivery?: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setResult(await post<{ email_delivery?: string }>("/auth/password/forgot", { email }));
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout>
      <AuthHeading title="Forgot your password?">Enter your work email and we&apos;ll send a reset link if the account exists.</AuthHeading>
      {result ? (
        result.email_delivery === "not_configured" ? (
          <div className="alert warning">
            Email is not set up for EMS yet, so no reset link can be sent. Ask your company admin (CEO or HR) to help you regain access.
          </div>
        ) : (
          <div className="alert success">If that email has an account, a reset link is on its way. The link expires in 1 hour.</div>
        )
      ) : (
        <form className="stack" onSubmit={submit} noValidate>
          <Field label="Work email" error={error?.fields.email}>
            {(id, inv) => <input id={id} className="input" type="email" autoComplete="email" required value={email}
              onChange={(e) => setEmail(e.target.value)} aria-invalid={inv} />}
          </Field>
          <FormError error={error?.code === "VALIDATION_FAILED" ? null : error} />
          <button className="btn dark block" disabled={busy || !email}>{busy ? "Sending…" : "Send reset link"}</button>
        </form>
      )}
      <p className="muted" style={{ textAlign: "center" }}><Link href="/login" style={{ fontWeight: 600 }}>Back to sign in</Link></p>
    </AuthLayout>
  );
}
