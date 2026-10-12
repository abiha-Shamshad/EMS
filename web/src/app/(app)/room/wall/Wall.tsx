"use client";

import { LiveKitRoom } from "@livekit/components-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { LiveFeeds } from "@/components/LiveFeeds";
import { Card, PageHeader } from "@/components/ui";
import { post, readCookie } from "@/lib/api";
import type { GridView } from "@/lib/types";

const KEY = "ems_grid";

function readGrid(): GridView | null {
  try {
    const raw = window.sessionStorage.getItem(KEY);
    return raw ? (JSON.parse(raw) as GridView) : null;
  } catch {
    return null;
  }
}

/** Browser-only CEO/COO video wall: one tile per live employee (webcam, screen inset), each its own logged view. */
export default function Wall() {
  const router = useRouter();
  const [grid] = useState(readGrid);
  const [now, setNow] = useState(() => Date.now());
  const [ended, setEnded] = useState(false);
  const [failed, setFailed] = useState<string[]>([]);
  const endedRef = useRef(false);
  const expiresAt = grid ? grid.opened_at + grid.expires_in_seconds * 1000 : 0;

  const endAll = useCallback(async (leave: boolean) => {
    if (!grid || endedRef.current) return;
    const results = await Promise.allSettled(grid.items.map((i) => post(`/room/stream/view/${i.view_id}/end`)));
    const stillOpen = grid.items.filter((_, n) => results[n]!.status === "rejected").map((i) => i.name);
    setFailed(stillOpen);                          // MEDIA_UNAVAILABLE: those views stay open until the viewer is removed
    if (stillOpen.length === 0) {
      endedRef.current = true;
      setEnded(true);
      window.sessionStorage.removeItem(KEY);
      if (leave) router.push("/room");
    }
  }, [grid, router]);

  useEffect(() => {
    if (!grid) return;
    const id = window.setInterval(() => {
      const t = Date.now();
      setNow(t);
      if (t >= expiresAt) void endAll(false);
    }, 1000);
    const onUnload = () => {
      if (endedRef.current) return;
      const csrf = readCookie("ems_csrf");
      for (const i of grid.items) {
        void fetch(`/api/v1/room/stream/view/${i.view_id}/end`, { method: "POST", keepalive: true, credentials: "same-origin",
          headers: csrf ? { "X-CSRF-Token": csrf } : {} });
      }
    };
    window.addEventListener("pagehide", onUnload);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("pagehide", onUnload);
    };
  }, [grid, expiresAt, endAll]);

  if (!grid) return <Card><p className="muted">No video wall is open in this tab. <Link href="/room">Back to the live room</Link></p></Card>;
  const left = Math.max(0, Math.round((expiresAt - now) / 1000));
  const live = left > 0 && !ended;
  return (
    <>
      <PageHeader title="Live video wall" subtitle={`${grid.items.length} people · live, not recorded · each person is told you are watching and why`}
        actions={<><span className="badge">{live ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")} left` : "Ended"}</span>
          <button className="btn danger" disabled={ended} onClick={() => void endAll(true)}>End all views</button></>} />
      {failed.length > 0 && <div className="alert error">Could not close the views of {failed.join(", ")} yet. Try again in a moment.</div>}
      {grid.items.length === 0 ? <Card><p className="muted">Nobody was live when the wall opened.</p></Card> : !live ? (
        <Card><p className="muted">The views have ended. Open the wall again from the live room with a new reason.</p></Card>
      ) : (
        <div className="wall">
          {grid.items.map((i) => (
            <div key={i.view_id} className="tile">
              <LiveKitRoom serverUrl={grid.livekit_url} token={i.token} connect audio={false} video={false}>
                <LiveFeeds compact />
              </LiveKitRoom>
              <div className="tile-foot"><b>{i.name}</b>
                <span className="row gap-sm">{i.camera && <span className="badge success">Webcam</span>}{i.screen && <span className="badge primary">Screen</span>}</span></div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
