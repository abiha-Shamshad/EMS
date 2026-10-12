"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar, Card, Empty, ErrorState, Field, FormError, Loading, Modal, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, post } from "@/lib/api";
import { label, relative, time } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { GridView, OpenView } from "@/lib/types";
import { useApi, usePoll } from "@/lib/useApi";

type Person = {
  user_id: string; name: string; department: string | null; presence: "active" | "idle" | "locked" | "on_break" | "offline"; since: string;
  current_task: { id: string; title: string } | null; stream: MediaState; camera: MediaState; minutes_late: number;
};
type MediaState = "live" | "paused" | "off" | "disabled";
type Live = { as_of: string; live_view_enabled: boolean; counts: Record<string, number>; items: Person[]; next_cursor: string | null };

const PRESENCE = ["active", "idle", "locked", "on_break", "offline"] as const;
const MEDIA_TEXT: Record<MediaState, string> = { live: "live", paused: "paused (break)", off: "off", disabled: "live view off" };

/** Screen 15 - CEO/COO live grid (API-025), with the offline fallback of screen 17 when the room cannot be loaded. */
export default function LiveRoomPage() {
  const router = useRouter();
  const { can, timeZone } = useSession();
  const [department, setDepartment] = useState("");
  const [presence, setPresence] = useState("");
  const live = useApi<Live>(can("room.view_live") ? "/room/live" : null, { department: department || null, presence: presence || null, limit: 48 });
  usePoll(live.reload, 15_000);
  const [viewing, setViewing] = useState<Person | "all" | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);

  if (!can("room.view_live")) return <NoAccess message="Only the CEO and COO can open the live room." />;

  async function openView() {
    if (!viewing) return;
    setBusy(true);
    setError(null);
    if (viewing === "all") {
      try {
        const g = await post<Omit<GridView, "opened_at">>("/room/stream/view-grid", { reason });
        window.sessionStorage.setItem("ems_grid", JSON.stringify({ ...g, opened_at: Date.now() }));
        router.push("/room/wall");
      } catch (e) {
        setError(e as ApiError);
        setBusy(false);
      }
      return;
    }
    try {
      const v = await post<Omit<OpenView, "subject">>("/room/stream/view", { subject_user_id: viewing.user_id, reason });
      // The token stays in this tab's memory store, never in the URL.
      window.sessionStorage.setItem(`ems_view_${v.view_id}`, JSON.stringify({ ...v, subject: viewing.name }));
      router.push(`/room/view/${v.view_id}`);
    } catch (e) {
      setError(e as ApiError);
      setBusy(false);
    }
  }

  const liveCount = (live.data?.items ?? []).filter((p) => p.stream === "live" || p.camera === "live").length;
  const depts = Array.from(new Set((live.data?.items ?? []).map((p) => p.department).filter(Boolean))) as string[];
  return (
    <>
      <PageHeader title="Live room" subtitle={live.data ? `Updated ${relative(live.data.as_of)} · refreshes every 15 seconds` : "Who is working on what right now"}
        actions={<>
          <select className="select" style={{ width: 170 }} value={department} onChange={(e) => setDepartment(e.target.value)} aria-label="Department">
            <option value="">All departments</option>{depts.map((d) => <option key={d}>{d}</option>)}</select>
          <select className="select" style={{ width: 150 }} value={presence} onChange={(e) => setPresence(e.target.value)} aria-label="Presence">
            <option value="">Any presence</option>{PRESENCE.map((p) => <option key={p} value={p}>{label(p)}</option>)}</select>
          <button className="btn" disabled={!live.data?.live_view_enabled || liveCount === 0}
            onClick={() => { setViewing("all"); setReason(""); setError(null); }}>Watch everyone live ({liveCount})</button>
        </>} />

      {live.error && !live.data ? (
        <Card>
          <div className="stack" style={{ alignItems: "center", textAlign: "center", padding: 24 }}>
            <h2 className="h2">The live room is offline</h2>
            <p className="muted">EMS can&apos;t load presence right now. Check-ins and heartbeats keep being recorded; the board fills in again when the connection returns.</p>
            <ErrorState error={live.error} retry={live.reload} />
          </div>
        </Card>
      ) : !live.data ? <Loading /> : (
        <>
          {!live.data.live_view_enabled && (
            <div className="alert warning">Live viewing (webcam and screen) is switched off for this company until the monitoring notice has had its legal review (OD-02). Presence, tasks and breaks still show below.</div>
          )}
          <div className="grid grid-4">
            {[["checked_in", "Checked in"], ["active", "Active"], ["idle", "Idle or locked"], ["on_break", "On break"], ["offline", "Offline"],
              ["on_leave", "On leave"], ["not_checked_in", "Not checked in"]].map(([k, text]) => (
              <div key={k} className="card stat"><span className="stat-label">{text}</span>
                <span className="stat-value">{k === "idle" ? (live.data!.counts.idle ?? 0) + (live.data!.counts.locked ?? 0) : live.data!.counts[k!] ?? 0}</span></div>
            ))}
          </div>
          {live.data.items.length === 0 ? <Card><Empty title="Nobody matches">People appear here when they check in with the EMS extension.</Empty></Card> : (
            <div className="live-grid">
              {live.data.items.map((p) => (
                <div key={p.user_id} className="card person">
                  <div className="row gap">
                    <Avatar name={p.name} />
                    <div className="grow"><b>{p.name}</b><div className="muted small">{p.department ?? "No department"}</div></div>
                    <span className={`presence-${p.presence}`} title={label(p.presence)}><span className="dot" /></span>
                  </div>
                  <div className="row gap wrap">
                    <StatusBadge value={p.presence} />
                    {p.minutes_late > 0 && <span className="badge warning">{p.minutes_late} min late</span>}
                  </div>
                  <div className="small"><span className="muted">Since </span>{time(p.since, timeZone)}</div>
                  <div className="small"><span className="muted">Task </span>{p.current_task?.title ?? "No task selected"}</div>
                  <div className="row between">
                    <span className="small muted">Webcam {MEDIA_TEXT[p.camera]} · Screen {MEDIA_TEXT[p.stream]}</span>
                    <button className="btn sm" disabled={p.stream !== "live" && p.camera !== "live"} onClick={() => { setViewing(p); setReason(""); setError(null); }}>View live</button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {viewing && (
        <Modal title={viewing === "all" ? `Watch everyone live (${liveCount})` : `View ${viewing.name} live`}
          subtitle={viewing === "all" ? "Each person is told right away who is viewing and why; one view per person is logged." : "The employee is told right away who is viewing and why; every view is logged."}
          onClose={() => setViewing(null)}
          footer={<><button className="btn ghost" onClick={() => setViewing(null)}>Cancel</button>
            <button className="btn" disabled={busy || reason.trim().length < 3} onClick={() => void openView()}>{busy ? "Opening…" : "Open live view"}</button></>}>
          <Field label="Reason" hint="3 to 200 characters, shown to each employee" error={error?.fields.reason}>
            {(id, inv) => <input id={id} className="input" maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} aria-invalid={inv}
              placeholder="e.g. Daily stand-up check" autoFocus />}
          </Field>
          <FormError error={error && !error.fields.reason ? error : null} />
        </Modal>
      )}
    </>
  );
}
