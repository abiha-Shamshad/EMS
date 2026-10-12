"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { Avatar, Card, Empty, ErrorState, Loading, LoadMore, NoAccess, PageHeader, StatusBadge } from "@/components/ui";
import { ApiError, get } from "@/lib/api";
import { label, time } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Employee = {
  user_id: string; name: string; title: string | null; department: string | null; manager: string | null; status: string;
  today: { state: string; since: string | null; minutes_late: number | null }; leave_balance_days: Record<string, number> | null;
};
type EmpPage = { items: Employee[]; next_cursor: string | null };

/** Screen 25 - employee directory (API-029). Managers see their team; HR and leadership see everyone. */
export default function EmployeesPage() {
  const router = useRouter();
  const { can, timeZone } = useSession();
  const [q, setQ] = useState("");
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"active" | "deactivated">("active");
  const list = useApi<EmpPage>(can("hr.manage") ? "/employees" : null, { q: query || null, status, limit: 50 });
  const [extra, setExtra] = useState<Employee[]>([]);
  const [cursor, setCursor] = useState<string | null | undefined>(undefined);
  const [error, setError] = useState<ApiError | null>(null);
  if (!can("hr.manage")) return <NoAccess message="Only HR, managers and leadership can open the directory." />;

  const next = cursor === undefined ? list.data?.next_cursor : cursor;
  const items = [...(list.data?.items ?? []), ...extra];
  async function more() {
    try {
      const p = await get<EmpPage>("/employees", { q: query || null, status, limit: 50, cursor: next });
      setExtra((e) => [...e, ...p.items]);
      setCursor(p.next_cursor);
    } catch (e) {
      setError(e as ApiError);
    }
  }
  const search = (v: string) => { setQuery(v); setExtra([]); setCursor(undefined); };

  return (
    <>
      <PageHeader title="Employee directory" subtitle="Today's state, leave balances and reporting lines" actions={<>
        <form onSubmit={(e) => { e.preventDefault(); search(q); }} className="row gap-sm">
          <input className="input" style={{ width: 220 }} placeholder="Search by name" value={q} onChange={(e) => setQ(e.target.value)} aria-label="Search" />
          <button className="btn ghost">Search</button>
        </form>
        <select className="select" style={{ width: 150 }} value={status} onChange={(e) => { setStatus(e.target.value as typeof status); setExtra([]); setCursor(undefined); }} aria-label="Status">
          <option value="active">Active</option><option value="deactivated">Deactivated</option></select>
      </>} />
      <Card flush>
        {list.error && !list.data ? <div style={{ padding: 20 }}><ErrorState error={list.error} retry={list.reload} /></div> : !list.data ? <Loading /> :
          items.length === 0 ? <Empty title="No one found">Try another name, or invite people from Users &amp; roles.</Empty> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Name</th><th>Department</th><th>Manager</th><th>Today</th><th>Leave balance (days)</th></tr></thead>
                <tbody>{items.map((e) => (
                  <tr key={e.user_id} className="clickable" onClick={() => router.push(`/hr/employees/${e.user_id}`)}>
                    <td><div className="row gap"><Avatar name={e.name} /><div><b>{e.name}</b><div className="muted small">{e.title ?? "—"}</div></div></div></td>
                    <td>{e.department ?? "—"}</td>
                    <td>{e.manager ?? "—"}</td>
                    <td><StatusBadge value={e.today.state} />{e.today.since && <span className="muted small"> {time(e.today.since, timeZone)}</span>}
                      {e.today.minutes_late ? <span className="badge warning" style={{ marginLeft: 6 }}>{e.today.minutes_late} min late</span> : null}</td>
                    <td>{e.leave_balance_days ? Object.entries(e.leave_balance_days).map(([k, v]) => `${label(k)} ${v}`).join(" · ") : <span className="muted small">No leave policy published</span>}</td>
                  </tr>
                ))}</tbody>
              </table>
            </div>
          )}
        {error && <div style={{ padding: 12 }}><ErrorState error={error} /></div>}
        <LoadMore cursor={next} onMore={() => void more()} />
      </Card>
    </>
  );
}
