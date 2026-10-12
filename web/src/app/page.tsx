"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { get } from "@/lib/api";
import type { Me } from "@/lib/types";

/** Entry point: the user's own dashboard when signed in, else the sign-in page. */
export default function Home() {
  const router = useRouter();
  useEffect(() => {
    get<Me>("/me")
      .then((me) => router.replace(me.active_org.setup_state === "account_created" ? "/setup/company" : `/dashboards/${me.dashboard}`))
      .catch((e: { code?: string }) => router.replace(e.code === "ORG_NOT_SELECTED" ? "/select-company" : "/login"));
  }, [router]);
  return <div className="center-page"><div className="spinner" aria-label="Loading" /></div>;
}
