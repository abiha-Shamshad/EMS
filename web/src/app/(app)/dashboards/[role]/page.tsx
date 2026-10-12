"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Icon, type IconName } from "@/components/icons";
import { Async, Card, Loading, PageHeader, Progress, StatusBadge } from "@/components/ui";
import { label, minutes, money, percent } from "@/lib/format";
import { useSession } from "@/lib/session";
import type { Gap, Permission, Tile } from "@/lib/types";
import { useApi } from "@/lib/useApi";

type Dashboard = {
  role: string; period: { label: string; from: string; to: string }; currency: string; tiles: Tile[]; unavailable: Gap[];
  budget_projects?: { project: string; budget: string; cost_to_date: string; ratio: string | null; entries_without_cost_rate?: number }[];
  notes?: string[];
};

/** What each role's dashboard is for, and the shortcuts that role uses most (shown only with the matching permission). */
type Shortcut = { href: string; label: string; icon: IconName; need?: Permission };
const ROLE_VIEW: Record<string, { title: string; focus: string; shortcuts: Shortcut[] }> = {
  ceo: { title: "CEO dashboard", focus: "Company overview: people, pipeline, cash and risk", shortcuts: [
    { href: "/room", label: "Live room", icon: "room", need: "room.view_live" },
    { href: "/crm/pipeline", label: "Pipeline", icon: "crm", need: "crm.manage" },
    { href: "/leakage", label: "Revenue leakage", icon: "leakage", need: "leakage.read" },
    { href: "/admin/members", label: "Users & roles", icon: "people", need: "members.manage" }] },
  cto: { title: "CTO dashboard", focus: "Delivery: projects, tasks and automations", shortcuts: [
    { href: "/projects", label: "Projects", icon: "projects" },
    { href: "/automation", label: "Automations", icon: "automation", need: "rules.manage" },
    { href: "/automation/logs", label: "Automation logs", icon: "automation", need: "rules.manage" }] },
  cfo: { title: "CFO dashboard", focus: "Money: invoices, collections, budgets and leakage", shortcuts: [
    { href: "/finance/invoices", label: "Invoices", icon: "finance", need: "finance.manage" },
    { href: "/leakage", label: "Revenue leakage", icon: "leakage", need: "leakage.read" },
    { href: "/crm/clients", label: "Clients", icon: "crm" }] },
  coo: { title: "COO dashboard", focus: "Operations: attendance, pipeline and project health", shortcuts: [
    { href: "/room", label: "Live room", icon: "room", need: "room.view_live" },
    { href: "/crm/deals", label: "Deals", icon: "crm", need: "crm.manage" },
    { href: "/projects", label: "Projects", icon: "projects" }] },
  hr: { title: "HR dashboard", focus: "People: attendance, leave and breaks", shortcuts: [
    { href: "/hr/employees", label: "Employees", icon: "people", need: "hr.manage" },
    { href: "/leave/approvals", label: "Leave approvals", icon: "leave" },
    { href: "/hr/breaks", label: "Break requests", icon: "clock", need: "hr.manage" },
    { href: "/hr/reports", label: "Attendance reports", icon: "clock", need: "hr.manage" }] },
  manager: { title: "Manager dashboard", focus: "Your team: attendance, leave, projects and deals", shortcuts: [
    { href: "/hr/employees", label: "My team", icon: "people", need: "hr.manage" },
    { href: "/leave/approvals", label: "Leave approvals", icon: "leave", need: "leave.decide" },
    { href: "/hr/breaks", label: "Break requests", icon: "clock", need: "leave.decide" },
    { href: "/projects", label: "Projects", icon: "projects" },
    { href: "/crm/pipeline", label: "Pipeline", icon: "crm", need: "crm.manage" },
    { href: "/hunter", label: "Lead Hunter", icon: "hunter", need: "hunter.use" }] },
  employee: { title: "My dashboard", focus: "Your tasks, time and leave", shortcuts: [
    { href: "/room/me", label: "My workday", icon: "clock", need: "room.self" },
    { href: "/projects", label: "My tasks", icon: "projects" },
    { href: "/leave", label: "Request leave", icon: "leave" }] },
};
const MONEY = new Set(["open_pipeline", "won", "invoiced", "collected", "outstanding", "overdue", "leakage"]);
const ICONS: Record<string, IconName> = {
  checked_in_now: "room", late_today: "clock", on_leave_today: "leave", open_pipeline: "crm", won: "check", invoiced: "finance",
  collected: "finance", outstanding: "finance", overdue: "alert", leakage: "leakage", projects_at_risk: "alert", projects_in_progress: "projects",
  tasks_done_this_week: "check", overdue_tasks: "alert", rule_runs_7d: "automation", active_automations: "automation", budget_use: "finance",
  attendance_rate: "people", active_projects: "projects", pipeline_by_stage: "crm", open_findings: "leakage", headcount: "people",
  present: "room", late: "clock", absent: "alert", pending_leave: "leave", break_overruns: "clock", idle_above_threshold: "clock",
  my_tasks: "projects", my_time_today: "clock", leave_balance: "leave", viewed_my_screen: "eye",
};
const LINKS: Record<string, string> = {
  checked_in_now: "/room", leakage: "/leakage", open_findings: "/leakage", open_pipeline: "/crm/pipeline", pending_leave: "/leave/approvals",
  outstanding: "/finance/invoices", overdue: "/finance/invoices", invoiced: "/finance/invoices", projects_at_risk: "/projects",
  active_projects: "/projects", projects_in_progress: "/projects", overdue_tasks: "/projects", rule_runs_7d: "/automation/logs",
  active_automations: "/automation", my_tasks: "/projects", viewed_my_screen: "/room/me", headcount: "/hr/employees", absent: "/hr/reports",
};

function TileValue({ tile, currency }: { tile: Tile; currency: string }) {
  const v = tile.value;
  if (MONEY.has(tile.key)) return <div className="stat-value">{money(v as string, currency)}</div>;
  if (tile.key === "budget_use") return <div className="stat-value">{percent(v as string | null)}</div>;
  if (tile.unit === "percent") return <div className="stat-value">{v === null ? "—" : `${v as number}%`}</div>;
  if (tile.unit === "minutes") return <div className="stat-value">{minutes(v as number)}</div>;
  if (Array.isArray(v)) {
    return (
      <div className="stack-sm" style={{ marginTop: 4 }}>
        {(v as { stage: string; count: number; amount: string }[]).map((s) => (
          <div key={s.stage} className="row between small"><span>{label(s.stage)} · {s.count}</span><b>{money(s.amount, currency)}</b></div>
        ))}
      </div>
    );
  }
  if (v && typeof v === "object") {
    return (
      <div className="row gap wrap" style={{ marginTop: 4 }}>
        {Object.entries(v as Record<string, number>).map(([k, n]) => (
          <span key={k} className="badge"><b style={{ color: "var(--text)" }}>{n}</b> {label(k)}</span>
        ))}
      </div>
    );
  }
  return <div className="stat-value">{v === null || v === undefined ? "—" : String(v)}</div>;
}

function TileCard({ tile, currency }: { tile: Tile; currency: string }) {
  const extras: string[] = [];
  if (tile.weighted) extras.push(`weighted ${money(tile.weighted as string, currency)}`);
  if (typeof tile.count === "number") extras.push(`${tile.count} record${tile.count === 1 ? "" : "s"}`);
  if (typeof tile.failed === "number") extras.push(`${tile.failed} failed`);
  if (typeof tile.not_checked_in === "number") extras.push(`${tile.not_checked_in} not checked in yet`);
  const href = LINKS[tile.key];
  const body = (
    <div className="card stat" style={{ height: "100%" }}>
      <div className="row between">
        <span className="stat-label">{tile.label}</span>
        <span className="icon-tile" style={{ width: 34, height: 34 }}><Icon name={ICONS[tile.key] ?? "dashboard"} size={16} /></span>
      </div>
      <TileValue tile={tile} currency={currency} />
      <div className="stat-foot">
        <span>{extras.join(" · ")}</span>
        <span title="Where this number comes from">Source: {tile.source}</span>
      </div>
    </div>
  );
  return href ? <Link href={href} style={{ color: "inherit", textDecoration: "none" }}>{body}</Link> : body;
}

/** Screens 07-12 - role dashboards (API-067). Every tile names its source; metrics EMS cannot source are listed with a reason. */
export default function DashboardPage() {
  const router = useRouter();
  const { role } = useParams<{ role: string }>();
  const { me } = useSession();
  // Role based: everyone sees their own role's dashboard only; any other /dashboards/<role> goes back to it.
  const own = role === me.dashboard;
  useEffect(() => { if (!own) router.replace(`/dashboards/${me.dashboard}`); }, [own, router, me.dashboard]);
  return own ? <RoleDashboard role={role} /> : <Loading />;
}

function RoleDashboard({ role }: { role: string }) {
  const { me, can } = useSession();
  const [period, setPeriod] = useState<"this_month" | "last_30_days">("this_month");
  const dash = useApi<Dashboard>(`/dashboards/${role}`, { period });
  const view = ROLE_VIEW[me.active_org.role] ?? ROLE_VIEW[role] ?? ROLE_VIEW.employee!;
  const shortcuts = view.shortcuts.filter((x) => !x.need || can(x.need));
  const first = me.user.name.split(" ")[0];
  const hour = new Date().getHours();
  const greeting = hour < 12 ? "Good morning" : hour < 18 ? "Good afternoon" : "Good evening";

  return (
    <>
      <PageHeader title={`${greeting}, ${first}!`} subtitle={`${view.title} · ${view.focus} · ${me.active_org.name}`} actions={
        <select className="select" style={{ width: 180 }} value={period} onChange={(e) => setPeriod(e.target.value as typeof period)} aria-label="Period">
          <option value="this_month">This month</option>
          <option value="last_30_days">Last 30 days</option>
        </select>
      } />
      {shortcuts.length > 0 && (
        <div className="row gap wrap" style={{ marginBottom: 16 }}>
          {shortcuts.map((x) => <Link key={x.href} href={x.href} className="btn ghost"><Icon name={x.icon} size={16} />{x.label}</Link>)}
        </div>
      )}
      <Async state={dash}>
        {(d) => (
          <div className="stack">
            <p className="muted small">{d.period.label} · amounts in {d.currency}</p>
            <div className="grid grid-4">{d.tiles.map((t) => <TileCard key={t.key} tile={t} currency={d.currency} />)}</div>
            {d.budget_projects && (
              <Card title="Project budgets" subtitle="Cost to date from logged time × member cost rates, against each fixed budget" flush>
                {d.budget_projects.length === 0 ? <p className="muted" style={{ padding: 20 }}>No projects with a budget yet.</p> : (
                  <div className="table-wrap">
                    <table className="table">
                      <thead><tr><th>Project</th><th className="num">Budget</th><th className="num">Cost to date</th><th style={{ width: "30%" }}>Used</th></tr></thead>
                      <tbody>{d.budget_projects.map((p) => (
                        <tr key={p.project}>
                          <td>{p.project}{p.entries_without_cost_rate ? <span className="badge warning" style={{ marginLeft: 8 }}>{p.entries_without_cost_rate} entries without a cost rate</span> : null}</td>
                          <td className="num">{money(p.budget, d.currency)}</td>
                          <td className="num">{money(p.cost_to_date, d.currency)}</td>
                          <td><div className="row gap"><div className="grow"><Progress ratio={p.ratio === null ? null : Number(p.ratio)} /></div>
                            <span className="small">{percent(p.ratio)}</span></div></td>
                        </tr>
                      ))}</tbody>
                    </table>
                  </div>
                )}
              </Card>
            )}
            {d.notes?.map((n) => <div key={n} className="alert info">{n}</div>)}
            {d.unavailable.length > 0 && (
              <Card title="Not available yet" subtitle="EMS shows no number it cannot source. These need a data source first.">
                <div className="list">
                  {d.unavailable.map((u) => (
                    <div key={u.key} className="list-item"><StatusBadge value="unavailable" text={label(u.key)} /><span className="muted">{u.reason}</span></div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        )}
      </Async>
    </>
  );
}
