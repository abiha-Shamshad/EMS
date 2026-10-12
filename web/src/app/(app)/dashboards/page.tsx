"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { Loading } from "@/components/ui";
import { useSession } from "@/lib/session";

export default function DashboardIndex() {
  const router = useRouter();
  const { me } = useSession();
  useEffect(() => router.replace(`/dashboards/${me.dashboard}`), [router, me.dashboard]);
  return <Loading />;
}
