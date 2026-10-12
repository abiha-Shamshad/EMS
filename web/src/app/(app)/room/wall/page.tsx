"use client";

import dynamic from "next/dynamic";

import { Loading, NoAccess } from "@/components/ui";
import { useSession } from "@/lib/session";

// Browser only: the tokens live in this tab's sessionStorage and each tile connects to LiveKit.
const Wall = dynamic(() => import("./Wall"), { ssr: false, loading: () => <Loading /> });

/** CEO/COO grid of every live employee's webcam (and screen), opened with one reason (POST /room/stream/view-grid). */
export default function VideoWallPage() {
  const { can } = useSession();
  if (!can("room.view_live")) return <NoAccess message="Only the CEO and COO can open the live room." />;
  return <Wall />;
}
