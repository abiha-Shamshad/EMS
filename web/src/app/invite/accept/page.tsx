"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { Field, FormError } from "@/components/ui";
import { ApiError, get, post, selectOrg } from "@/lib/api";
import type { Me } from "@/lib/types";

type Accepted = { org: { id: string; name: string }; membership: { role: string }; next_step: string };

/** Accept an invitation link (API-012): new people create their account here; signed-in people just join. */
function AcceptForm() {
  const router = useRouter();
  const token = useSearchParams().get("token") ?? "";
  const [signedIn, setSignedIn] = useState<string | null | undefined>(undefined);
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [done, setDone] = useState<Accepted | null>(null);

  useEffect(() => {
    get<Me>("/me").then((me) => setSignedIn(me.user.name)).catch((e: ApiError) => setSignedIn(e.code === "ORG_NOT_SELECTED" ? "you" : null));
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await post<Accepted>("/invitations/accept", signedIn ? { token } : { token, name, password });
      selectOrg(res.org.id);
      setDone(res);
    } catch (err) {
      setError(err as ApiError);
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return <AuthLayout><AuthHeading title="Invitation link missing">Open the link your company shared with you.</AuthHeading></AuthLayout>;
  }
  if (done) {
    return (
      <AuthLayout>
        <AuthHeading eyebrow="You're in" title={`Welcome to ${done.org.name}`}>
          You joined as {done.membership.role}. Next, install the EMS Chrome extension to check in and out of your workday.
        </AuthHeading>
        <button className="btn dark block" onClick={() => router.replace("/")}>Go to my dashboard</button>
      </AuthLayout>
    );
  }
  return (
    <AuthLayout>
      <AuthHeading eyebrow="Invitation" title="Join your team on EMS">
        {signedIn ? `Signed in as ${signedIn}. Accept to add this company to your account.` : "Create your account to accept the invitation."}
      </AuthHeading>
      {signedIn === undefined ? <div className="spinner" /> : (
        <form className="stack" onSubmit={submit} noValidate>
          {!signedIn && (
            <>
              <Field label="Your name" error={error?.fields.name}>
                {(id, inv) => <input id={id} className="input" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} aria-invalid={inv} />}
              </Field>
              <Field label="Password" error={error?.fields.password} hint="12 to 128 characters">
                {(id, inv) => <input id={id} className="input" type="password" autoComplete="new-password" value={password}
                  onChange={(e) => setPassword(e.target.value)} aria-invalid={inv} />}
              </Field>
            </>
          )}
          <FormError error={error?.code === "VALIDATION_FAILED" ? null : error} />
          {error?.code === "AUTHENTICATION_REQUIRED" && (
            <Link className="btn ghost" href={`/login?next=${encodeURIComponent(`/invite/accept?token=${token}`)}`}>Sign in to accept</Link>
          )}
          <button className="btn dark block" disabled={busy || (!signedIn && (!name || !password))}>{busy ? "Joining…" : "Accept invitation"}</button>
        </form>
      )}
    </AuthLayout>
  );
}

export default function AcceptInvitationPage() {
  return <Suspense><AcceptForm /></Suspense>;
}
