import { date, minutes } from "@/lib/format";

import { StatusBadge } from "./ui";

export type AttendanceDay = { date: string; status: string; check_in?: string; check_out?: string | null; minutes_late?: number; active?: number;
  idle?: number; locked?: number; on_break?: number; offline?: number };
export type Attendance = { user_id: string; days: AttendanceDay[]; totals: { present_days: number; late_days: number; active_minutes: number } };

/** Timesheet rows from API-030. Times are company-local. */
export function AttendanceTable({ a }: { a: Attendance }) {
  return (
    <div className="stack">
      <div className="grid grid-3">
        <div className="card stat"><span className="stat-label">Days present</span><span className="stat-value">{a.totals.present_days}</span></div>
        <div className="card stat"><span className="stat-label">Days late</span><span className="stat-value">{a.totals.late_days}</span></div>
        <div className="card stat"><span className="stat-label">Active time</span><span className="stat-value">{minutes(a.totals.active_minutes)}</span></div>
      </div>
      <div className="card flush table-wrap">
        <table className="table">
          <thead><tr><th>Date</th><th>Status</th><th>In</th><th>Out</th><th className="num">Late</th><th className="num">Active</th><th className="num">Idle / locked</th>
            <th className="num">Breaks</th><th className="num">Offline</th></tr></thead>
          <tbody>{[...a.days].reverse().map((d) => (
            <tr key={d.date}>
              <td>{date(d.date)}</td><td><StatusBadge value={d.status} /></td><td>{d.check_in ?? "—"}</td><td>{d.check_out ?? (d.check_in ? "open" : "—")}</td>
              <td className="num">{d.minutes_late ? `${d.minutes_late} min` : "—"}</td><td className="num">{minutes(d.active)}</td>
              <td className="num">{d.check_in ? minutes((d.idle ?? 0) + (d.locked ?? 0)) : "—"}</td><td className="num">{minutes(d.on_break)}</td><td className="num">{minutes(d.offline)}</td>
            </tr>
          ))}</tbody>
        </table>
      </div>
    </div>
  );
}
