"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { post } from "@/lib/api";

/** Signed in, but not an active member of any company (left, deactivated, or invitation not yet accepted). */
export default function NoCompanyPage() {
  const router = useRouter();
  return (
    <AuthLayout>
      <AuthHeading title="No company yet">
        Your account is not part of an active company. Open the invitation link your company shared, or create your own company.
      </AuthHeading>
      <Link className="btn dark block" href="/signup">Create a company account</Link>
      <button className="btn ghost block" onClick={() => void post("/auth/logout").finally(() => router.replace("/login"))}>Sign out</button>
    </AuthLayout>
  );
}
