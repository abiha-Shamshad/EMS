"use client";

import dynamic from "next/dynamic";
import { useParams } from "next/navigation";

import { Loading, NoAccess } from "@/components/ui";
import { useSession } from "@/lib/session";

// Rendered in the browser only: it reads the view token from sessionStorage and connects to LiveKit.
const Viewer = dynamic(() => import("./Viewer"), { ssr: false, loading: () => <Loading /> });

/** Screen 16 - full-screen live view of one employee (API-026/027). Subscribe-only token, 15 minutes, never recorded. */
export default function LiveViewPage() {
  const { viewId } = useParams<{ viewId: string }>();
  const { can } = useSession();
  if (!can("room.view_live")) return <NoAccess />;
  return <Viewer viewId={viewId} />;
}
