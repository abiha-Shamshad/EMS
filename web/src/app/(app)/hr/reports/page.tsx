"use client";

import { useState } from "react";

import { DailyReport, type Report } from "@/components/DailyReport";
import { Async, Card, NoAccess, PageHeader, Tabs } from "@/components/ui";
import { date, minutes, today } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

type Weekly = { week: string; days: Report[]; totals: { present: number; on_leave: number; absent_unexplained: number; active_minutes_total: number } };

/** ISO week ("2026-W42") of a YYYY-MM-DD date. */
function isoWeek(day: string): string {
  const d = new Date(`${day}T00:00:00Z`);
  const dow = (d.getUTCDay() + 6) % 7;
  d.setUTCDate(d.getUTCDate() - dow + 3);
  const firstThursday = new Date(Date.UTC(d.getUTCFullYear(), 0, 4));
  const week = 1 + Math.round(((d.getTime() - firstThursday.getTime()) / 86400000 - 3 + ((firstThursday.getUTCDay() + 6) % 7)) / 7);
  return `${d.getUTCFullYear()}-W${String(week).padStart(2, "0")}`;
}

/** Screen 31 - daily and weekly HR reports (API-034). The daily report is also sent to leadership at 23:30. */
export default function ReportsPage() {
  const { can, timeZone } = useSession();
  const [mode, setMode] = useState<"daily" | "weekly">("daily");
  const [day, setDay] = useState(today(timeZone));
  const daily = useApi<Report>(can("hr.manage") && mode === "daily" ? "/hr/reports/daily" : null, { date: day });
  const weekly = useApi<Weekly>(can("hr.manage") && mode === "weekly" ? "/hr/reports/daily" : null, { week: isoWeek(day) });
  if (!can("hr.manage")) return <NoAccess message="Only HR, managers and leadership can view reports." />;

  return (
    <>
      <PageHeader title="Daily & weekly reports" subtitle="Attendance, lateness and review signals" actions={
        <input className="input" type="date" style={{ width: 170 }} value={day} max={today(timeZone)} onChange={(e) => setDay(e.target.value)} aria-label="Date" />} />
      <Tabs value={mode} onChange={setMode} options={[{ value: "daily", label: "Daily" }, { value: "weekly", label: "Weekly" }]} />
      {mode === "daily" ? <Async state={daily}>{(r) => <DailyReport r={r} />}</Async> : (
        <Async state={weekly}>
          {(w) => (
            <div className="stack">
              <div className="grid grid-4">
                {[["Present (person-days)", w.totals.present], ["On leave", w.totals.on_leave], ["Absent (unexplained)", w.totals.absent_unexplained],
                  ["Active time", minutes(w.totals.active_minutes_total)]].map(([k, v]) => (
                  <div key={k} className="card stat"><span className="stat-label">{k}</span><span className="stat-value">{v}</span></div>
                ))}
              </div>
              <Card title={`Week ${w.week}`} flush>
                <div className="table-wrap">
                  <table className="table">
                    <thead><tr><th>Day</th><th className="num">Present</th><th className="num">On leave</th><th className="num">Absent</th><th className="num">Late</th><th className="num">Active</th></tr></thead>
                    <tbody>{w.days.map((r) => (
                      <tr key={r.date}><td>{date(r.date)}</td><td className="num">{r.present}</td><td className="num">{r.on_leave}</td>
                        <td className="num">{r.absent_unexplained}</td><td className="num">{r.late.length}</td><td className="num">{minutes(r.active_minutes_total)}</td></tr>
                    ))}</tbody>
                  </table>
                </div>
              </Card>
            </div>
          )}
        </Async>
      )}
    </>
  );
}
