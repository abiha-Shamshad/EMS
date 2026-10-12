"use client";

import { useState } from "react";

import { AttendanceTable, type Attendance } from "@/components/AttendanceTable";
import { Async, PageHeader } from "@/components/ui";
import { today } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Member, Page } from "@/lib/types";
import { useApi } from "@/lib/useApi";

function shift(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

/** Screen 26 - attendance and timesheets (API-030). Everyone sees their own; HR scope sees others. */
export default function AttendancePage() {
  const { me, can, timeZone } = useSession();
  const end0 = today(timeZone);
  const [to, setTo] = useState(end0);
  const [from, setFrom] = useState(shift(end0, -6));
  const [who, setWho] = useState(me.user.id);
  const members = useApi<Page<Member>>(can("hr.manage") ? "/members" : null, { limit: 100, status: "active" });
  const att = useApi<Attendance>("/attendance", { user_id: who, from, to });

  return (
    <>
      <PageHeader title="Attendance & timesheets" subtitle="Company-local times. Up to 62 days at a time." actions={<>
        {can("hr.manage") && (
          <select className="select" style={{ width: 200 }} value={who} onChange={(e) => setWho(e.target.value)} aria-label="Person">
            {(members.data?.items ?? [{ user_id: me.user.id, name: me.user.name }]).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
          </select>
        )}
        <input className="input" type="date" style={{ width: 160 }} value={from} max={to} onChange={(e) => setFrom(e.target.value)} aria-label="From" />
        <input className="input" type="date" style={{ width: 160 }} value={to} min={from} max={end0} onChange={(e) => setTo(e.target.value)} aria-label="To" />
      </>} />
      <Async state={att}>{(a) => <AttendanceTable a={a} />}</Async>
    </>
  );
}
