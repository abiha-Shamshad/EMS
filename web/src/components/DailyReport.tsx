import { minutes } from "@/lib/format";

export type Report = {
  date: string; headcount: number; present: number; on_leave: number; absent_unexplained: number; not_checked_in?: number;
  late: { name: string; minutes: number }[]; idle_over_threshold: { name: string; idle_minutes: number }[];
  break_over_allowance: { name: string; minutes_over: number }[]; active_minutes_total: number; notes?: string;
};

/** One day of the HR report (API-034). Idle time is a review signal, never a score (Section 17). */
export function DailyReport({ r }: { r: Report }) {
  return (
    <div className="stack">
      <div className="grid grid-4">
        {[["Headcount", r.headcount], ["Present", r.present], ["On leave", r.on_leave], ["Absent (unexplained)", r.absent_unexplained]].map(([k, v]) => (
          <div key={k} className="card stat"><span className="stat-label">{k}</span><span className="stat-value">{v}</span></div>
        ))}
      </div>
      <div className="grid grid-3">
        <div className="card"><h3 className="h3">Late arrivals</h3>
          {r.late.length === 0 ? <p className="muted">Nobody was late.</p> : r.late.map((x) => <div key={x.name} className="row between list-item"><span>{x.name}</span><span className="badge warning">{x.minutes} min</span></div>)}
        </div>
        <div className="card"><h3 className="h3">Idle above threshold</h3>
          {r.idle_over_threshold.length === 0 ? <p className="muted">No one above the threshold.</p> : r.idle_over_threshold.map((x) => <div key={x.name} className="row between list-item"><span>{x.name}</span><span className="badge">{minutes(x.idle_minutes)}</span></div>)}
        </div>
        <div className="card"><h3 className="h3">Breaks over allowance</h3>
          {r.break_over_allowance.length === 0 ? <p className="muted">All breaks within the allowance.</p> : r.break_over_allowance.map((x) => <div key={x.name} className="row between list-item"><span>{x.name}</span><span className="badge info">+{minutes(x.minutes_over)}</span></div>)}
        </div>
      </div>
      <p className="muted small">Active time across the team: {minutes(r.active_minutes_total)}. {r.notes}</p>
    </div>
  );
}
