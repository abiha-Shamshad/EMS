"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, useState, type FormEvent } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { Field, FormError } from "@/components/ui";
import { ApiError, post } from "@/lib/api";

/** Screen 04 - choose a new password from a reset link (API-006). */
function ResetForm() {
  const token = useSearchParams().get("token") ?? "";
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState(false);
  const checks = [
    { ok: pw.length >= 12, text: "At least 12 characters" },
    { ok: pw.length <= 128, text: "At most 128 characters" },
    { ok: pw.length > 0 && pw === confirm, text: "Both passwords match" },
  ];

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await post("/auth/password/reset", { token, new_password: pw });
      setDone(true);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <AuthLayout>
        <AuthHeading title="Reset link missing">Open the link from your reset email, or request a new one.</AuthHeading>
        <Link className="btn dark block" href="/forgot-password">Request a new link</Link>
      </AuthLayout>
    );
  }
  return (
    <AuthLayout>
      <AuthHeading title="Set a new password">Choose a password you don&apos;t use anywhere else. You&apos;ll be signed out on every device.</AuthHeading>
      {done ? (
        <>
          <div className="alert success">Password changed. Sign in with your new password.</div>
          <Link className="btn dark block" href="/login">Go to sign in</Link>
        </>
      ) : (
        <form className="stack" onSubmit={submit} noValidate>
          <Field label="New password" error={error?.fields.new_password}>
            {(id, inv) => <input id={id} className="input" type="password" autoComplete="new-password" value={pw} onChange={(e) => setPw(e.target.value)} aria-invalid={inv} />}
          </Field>
          <Field label="Confirm new password">
            {(id) => <input id={id} className="input" type="password" autoComplete="new-password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />}
          </Field>
          <ul className="stack-sm small" style={{ margin: 0, paddingLeft: 18 }}>
            {checks.map((c) => <li key={c.text} style={{ color: c.ok ? "var(--success)" : "var(--muted)" }}>{c.text}</li>)}
          </ul>
          <FormError error={error?.code === "VALIDATION_FAILED" ? null : error} />
          {error?.code === "RESET_TOKEN_EXPIRED" && <Link href="/forgot-password">Request a new link</Link>}
          <button className="btn dark block" disabled={busy || !checks.every((c) => c.ok)}>{busy ? "Saving…" : "Change password"}</button>
        </form>
      )}
    </AuthLayout>
  );
}

export default function ResetPasswordPage() {
  return <Suspense><ResetForm /></Suspense>;
}
