"use client";

import Link from "next/link";
import { useParams } from "next/navigation";

import { AttendanceTable, type Attendance } from "@/components/AttendanceTable";
import { Async, Avatar, Card, Empty, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { label, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Graph = { node: { kind: string; label: string }; neighbors: { kind: string; label: string; depth: number; via: string[] }[] };

function daysAgo(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() - n);
  return d.toISOString().slice(0, 10);
}

/** Screen 25 detail: one person's profile, last two weeks of attendance (API-030) and related work from graph memory (API-068). */
export default function EmployeeDetailPage() {
  const { can } = useSession();
  return can("hr.manage") ? <EmployeeDetail /> : <><PageHeader title="Employee" /><NoAccess /></>;
}

function EmployeeDetail() {
  const { userId } = useParams<{ userId: string }>();
  const { timeZone } = useSession();
  const end = today(timeZone);
  const members = useApi<Page<Member>>("/members", { limit: 100 });
  const att = useApi<Attendance>("/attendance", { user_id: userId, from: daysAgo(end, 13), to: end });
  const graph = useApi<Graph>("/graph/neighbors", { kind: "person", ref_id: userId, depth: 2 });
  const m = members.data?.items.find((x) => x.user_id === userId);
  const manager = m?.manager_id ? members.data?.items.find((x) => x.user_id === m.manager_id) : undefined;

  return (
    <>
      <PageHeader title={m?.name ?? "Employee"} subtitle={<Link href="/hr/employees">← Back to the directory</Link>} />
      <div className="grid grid-3">
        <Card title="Profile">
          {m ? (
            <div className="stack">
              <div className="row gap"><Avatar name={m.name} large /><div><b>{m.name}</b><div className="muted">{m.title ?? "No title"}</div></div></div>
              <dl className="kv">
                <dt>Role</dt><dd>{label(m.role)}</dd>
                <dt>Department</dt><dd>{m.department ?? "—"}</dd>
                <dt>Manager</dt><dd>{manager?.name ?? "—"}</dd>
                <dt>Status</dt><dd><StatusBadge value={m.status} /></dd>
              </dl>
            </div>
          ) : <p className="muted">Loading…</p>}
        </Card>
        <Card title="Related work" subtitle="From graph memory: projects, deals and people around this person" className="span-2">
          {graph.error?.code === "NOT_FOUND" ? <Empty title="Nothing linked yet">Assigned tasks and owned deals or projects appear here.</Empty> : (
          <Async state={graph}>
            {(g) => g.neighbors.length === 0 ? <Empty title="Nothing linked yet">Assigned tasks and owned deals or projects appear here.</Empty> : (
              <div className="row gap wrap">{g.neighbors.map((n) => (
                <span key={`${n.kind}-${n.label}`} className="badge primary" title={n.via.join(" → ")}>{label(n.kind)}: {n.label}</span>
              ))}</div>
            )}
          </Async>
          )}
        </Card>
      </div>
      <h2 className="h3">Last 14 days</h2>
      <Async state={att}>{(a) => <AttendanceTable a={a} />}</Async>
    </>
  );
}
