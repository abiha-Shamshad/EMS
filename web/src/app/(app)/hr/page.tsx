"use client";

import Link from "next/link";

import { DailyReport, type Report } from "@/components/DailyReport";
import { Icon, type IconName } from "@/components/icons";
import { Async, Card, NoAccess, PageHeader } from "@/components/ui";
import { date } from "@/lib/format";
import { useSession } from "@/lib/session";
import { useApi } from "@/lib/useApi";

const LINKS: [string, string, string, IconName][] = [
  ["/hr/employees", "Employee directory", "Who is in today, leave balances, details", "people"],
  ["/hr/attendance", "Attendance & timesheets", "Check-in, check-out and presence minutes per day", "clock"],
  ["/leave/approvals", "Leave approvals", "Requests waiting for your decision", "leave"],
  ["/hr/breaks", "Break log", "Break requests above the allowance and the log", "clock"],
  ["/hr/reports", "Daily & weekly reports", "Attendance, lateness, idle review signals", "report"],
  ["/hr/agent", "HR Agent", "Ask questions answered from EMS records", "agent"],
  ["/hr/policies", "Policies & rules", "Leave, attendance, breaks, monitoring notice", "shield"],
];

/** Screen 24 - HRM dashboard: today's report (API-034) plus the HR work queues. */
export default function HrDashboardPage() {
  const { can, me } = useSession();
  const report = useApi<Report>(can("hr.manage") ? "/hr/reports/daily" : null);
  const pending = useApi<{ items: unknown[] }>(can("leave.decide") ? "/leave-requests" : null, { scope: "to_decide" });
  const breaks = useApi<{ items: { can_decide: boolean }[] }>(can("leave.decide") ? "/room/breaks" : null, { status: "requested" });
  if (!can("hr.manage")) return <NoAccess message="Only HR, managers and leadership can open People & HR." />;
  return (
    <>
      <PageHeader title="People & HR" subtitle={me.active_org.role === "manager" ? "Your team today" : "Your company today"} />
      {can("leave.decide") && (
        <div className="grid grid-2">
          <Link href="/leave/approvals" className="card stat" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="stat-label">Leave requests waiting for you</span><span className="stat-value">{pending.data?.items.length ?? "…"}</span></Link>
          <Link href="/hr/breaks" className="card stat" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="stat-label">Break requests waiting for you</span>
            <span className="stat-value">{breaks.data ? breaks.data.items.filter((b) => b.can_decide).length : "…"}</span></Link>
        </div>
      )}
      <Card title="Today" subtitle={report.data ? date(report.data.date) : undefined} actions={<Link href="/hr/reports" className="btn ghost sm">Reports</Link>}>
        <Async state={report}>{(r) => <DailyReport r={r} />}</Async>
      </Card>
      <div className="grid grid-3">
        {LINKS.map(([href, title, text, icon]) => (
          <Link key={href} href={href} className="card row gap" style={{ color: "inherit", textDecoration: "none" }}>
            <span className="icon-tile"><Icon name={icon} /></span>
            <span><b>{title}</b><span className="muted small" style={{ display: "block" }}>{text}</span></span>
          </Link>
        ))}
      </div>
    </>
  );
}
