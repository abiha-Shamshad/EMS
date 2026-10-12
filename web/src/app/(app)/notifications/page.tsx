"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Card, Empty, ErrorState, Loading, LoadMore, PageHeader, Tabs } from "@/components/ui";
import { ApiError, get, post } from "@/lib/api";
import { dateTime, relative } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Note = { id: string; kind: string; title: string; ref_type: string | null; ref_id: string | null; read: boolean; created_at: string };
type NotePage = { items: Note[]; unread: number; next_cursor: string | null };

/** Where a notification leads (by the record it is about). */
function target(n: Note): string | null {
  switch (n.ref_type) {
    case "leave_request": return n.kind === "leave.decided" ? "/leave" : "/leave/approvals";
    case "break": return n.kind === "room.break_decided" ? "/room/me" : "/hr/breaks";
    case "invitation": case "membership": return "/admin/members";
    case "stream_view": return "/room/me";
    case "hr_report": return "/hr/reports";
    case "deal": return "/crm/pipeline";
    case "task": return "/projects";
    case "prospect": return "/hunter";
    case "invoice": return "/finance/invoices";
    case "employee": return "/hr/employees";
    default: return null;
  }
}

/** Screen 13 - notifications (API-069/070). */
export default function NotificationsPage() {
  const router = useRouter();
  const { timeZone } = useSession();
  const [filter, setFilter] = useState<"all" | "unread">("all");
  const first = useApi<NotePage>("/notifications", { unread_only: filter === "unread", limit: 25 });
  const [more, setMore] = useState<{ filter: string; items: Note[]; cursor: string | null } | null>(null);
  const [read, setRead] = useState<Set<string>>(new Set());
  const [error, setError] = useState<ApiError | null>(null);

  const extra = more?.filter === filter ? more : null;
  const items = [...(first.data?.items ?? []), ...(extra?.items ?? [])].map((n) => (read.has(n.id) ? { ...n, read: true } : n));
  const cursor = extra ? extra.cursor : first.data?.next_cursor;
  const unread = Math.max(0, (first.data?.unread ?? 0) - read.size);         // only unread items are ever added to `read`

  async function loadMore() {
    try {
      const p = await get<NotePage>("/notifications", { unread_only: filter === "unread", cursor, limit: 25 });
      setMore({ filter, items: [...(extra?.items ?? []), ...p.items], cursor: p.next_cursor });
    } catch (e) {
      setError(e as ApiError);
    }
  }

  async function open(n: Note) {
    if (!n.read) {
      await post(`/notifications/${n.id}/read`).catch(() => undefined);
      setRead((r) => new Set(r).add(n.id));
    }
    const href = target(n);
    if (href) router.push(href);
  }

  async function markAll() {
    const pending = items.filter((n) => !n.read);
    await Promise.all(pending.map((n) => post(`/notifications/${n.id}/read`).catch(() => undefined)));
    setRead(new Set());
    setMore(null);
    first.reload();
  }

  return (
    <>
      <PageHeader title="Notifications" subtitle={`${unread} unread`} actions={unread > 0 && <button className="btn ghost" onClick={() => void markAll()}>Mark shown as read</button>} />
      <Tabs value={filter} onChange={(f) => { setFilter(f); setRead(new Set()); }} options={[{ value: "all", label: "All" }, { value: "unread", label: "Unread" }]} />
      <Card flush>
        {first.error && !first.data ? <div style={{ padding: 20 }}><ErrorState error={first.error} retry={first.reload} /></div>
          : !first.data ? <Loading />
          : items.length === 0 ? <Empty title={filter === "unread" ? "You're all caught up" : "No notifications yet"}>Leave requests, breaks, invitations and screen views appear here.</Empty>
          : (
            <div className="list" style={{ padding: "0 20px" }}>
              {items.map((n) => (
                <button key={n.id} className="list-item" onClick={() => void open(n)}
                  style={{ background: "none", border: 0, borderBottom: "1px solid var(--border)", textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit" }}>
                  <span className="dot" style={{ color: n.read ? "transparent" : "var(--primary)", marginTop: 7 }} aria-label={n.read ? "Read" : "Unread"} />
                  <span className="grow">
                    <b style={{ fontWeight: n.read ? 500 : 650 }}>{n.title}</b>
                    <span className="muted small" style={{ display: "block" }} title={dateTime(n.created_at, timeZone)}>{relative(n.created_at)}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        {error && <div style={{ padding: 12 }}><ErrorState error={error} /></div>}
        <LoadMore cursor={cursor} onMore={() => void loadMore()} />
      </Card>
    </>
  );
}
