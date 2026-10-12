"use client";

import { LiveKitRoom } from "@livekit/components-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { LiveFeeds } from "@/components/LiveFeeds";
import { Card, PageHeader } from "@/components/ui";
import { ApiError, post, readCookie } from "@/lib/api";
import type { OpenView } from "@/lib/types";

function readView(viewId: string): OpenView | null {
  try {
    const raw = window.sessionStorage.getItem(`ems_view_${viewId}`);
    return raw ? (JSON.parse(raw) as OpenView) : null;
  } catch {
    return null;
  }
}

/** Browser-only part of screen 16: the token lives in this tab's sessionStorage, never in the URL. */
export default function Viewer({ viewId }: { viewId: string }) {
  const router = useRouter();
  const [view] = useState(() => readView(viewId));
  const [expiresAt] = useState(() => Date.now() + (view?.expires_in_seconds ?? 0) * 1000);
  const [now, setNow] = useState(() => Date.now());
  const [ended, setEnded] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const endedRef = useRef(false);

  const end = useCallback(async (leave: boolean) => {
    if (endedRef.current) return;
    try {
      await post(`/room/stream/view/${viewId}/end`);
      endedRef.current = true;
      setEnded(true);
      window.sessionStorage.removeItem(`ems_view_${viewId}`);
      if (leave) router.push("/room");
    } catch (e) {
      setError(e as ApiError);                       // MEDIA_UNAVAILABLE: the view stays open until the viewer is really removed
    }
  }, [viewId, router]);

  useEffect(() => {
    if (!view) return;
    const id = window.setInterval(() => {
      const t = Date.now();
      setNow(t);
      if (t >= expiresAt) void end(false);           // token lifetime reached: end the view (the worker sweep is the backstop)
    }, 1000);
    // Closing the tab still ends the view (keepalive survives unload).
    const onUnload = () => {
      if (endedRef.current) return;
      const csrf = readCookie("ems_csrf");
      void fetch(`/api/v1/room/stream/view/${viewId}/end`, { method: "POST", keepalive: true, credentials: "same-origin",
        headers: csrf ? { "X-CSRF-Token": csrf } : {} });
    };
    window.addEventListener("pagehide", onUnload);
    return () => {
      window.clearInterval(id);
      window.removeEventListener("pagehide", onUnload);
    };
  }, [view, viewId, expiresAt, end]);

  if (!view) return <Card><p className="muted">This view is no longer open in this tab. <Link href="/room">Back to the live room</Link></p></Card>;
  const left = Math.max(0, Math.round((expiresAt - now) / 1000));
  const live = left > 0 && !ended;
  return (
    <>
      <PageHeader title={`${view.subject} live`} subtitle={`Live, not recorded · ${view.subject} can see that you are viewing`}
        actions={<><span className="badge">{live ? `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")} left` : "Ended"}</span>
          <button className="btn danger" disabled={ended} onClick={() => void end(true)}>End view</button></>} />
      {error && <div className="alert error">{error.message}</div>}
      {live ? (
        <LiveKitRoom serverUrl={view.livekit_url} token={view.token} connect audio={false} video={false}
          onError={(e) => setError(new ApiError(503, { code: "MEDIA_UNAVAILABLE", message: `Could not connect to the media server: ${e.message}`, retryable: true, details: {} }))}>
          <LiveFeeds />
        </LiveKitRoom>
      ) : (
        <div className="video-stage"><span>The view has ended. Open it again from the live room with a new reason.</span></div>
      )}
    </>
  );
}
