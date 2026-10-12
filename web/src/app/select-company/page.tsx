"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AuthHeading, AuthLayout } from "@/components/AuthLayout";
import { ApiError, get, post, selectOrg } from "@/lib/api";
import { label } from "@/lib/format";
import type { Me } from "@/lib/types";

type Org = { id: string; name: string; role?: string };

function knownOrgs(): Org[] {
  try {
    return JSON.parse(window.sessionStorage.getItem("ems_orgs") ?? "[]") as Org[];
  } catch {
    return [];
  }
}

/** People in several companies pick one; the choice is sent as X-Org-Id (Section 7.1). */
export default function SelectCompanyPage() {
  const router = useRouter();
  const [orgs, setOrgs] = useState<Org[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    selectOrg(null);
    get<Me>("/me")
      .then((me) => {
        selectOrg(me.active_org.id);                     // only one company: nothing to choose
        router.replace(`/dashboards/${me.dashboard}`);
      })
      .catch((e: ApiError) => {
        if (e.code === "ORG_NOT_SELECTED") {
          const names = new Map(knownOrgs().map((o) => [o.id, o]));
          setOrgs(((e.details.organizations as string[]) ?? []).map((id) => names.get(id) ?? { id, name: `Company ${id.slice(0, 8)}` }));
        } else if (e.code === "AUTHENTICATION_REQUIRED") router.replace("/login");
        else setError(e.message);
      });
  }, [router]);

  async function choose(id: string) {
    selectOrg(id);
    try {
      const me = await get<Me>("/me");
      router.replace(`/dashboards/${me.dashboard}`);
    } catch (e) {
      selectOrg(null);
      setError((e as ApiError).message);
    }
  }

  return (
    <AuthLayout>
      <AuthHeading title="Choose a company">You belong to more than one company on EMS.</AuthHeading>
      {error && <div className="alert error">{error}</div>}
      {orgs === null && !error && <div className="spinner" />}
      {orgs?.map((o) => (
        <button key={o.id} className="btn ghost block" onClick={() => void choose(o.id)}>
          {o.name}{o.role && <span className="muted small"> · {label(o.role)}</span>}
        </button>
      ))}
      <button className="link-btn" onClick={() => void post("/auth/logout").finally(() => router.replace("/login"))}>Sign out</button>
    </AuthLayout>
  );
}
