"""Role dashboards (API-067, spec Section 18). Every tile names its source; a metric EMS cannot source is listed under
`unavailable` with a reason and never shown with sample numbers. Money tiles use the company's base currency.

Definitions (AUD-06/07): outstanding = sum(amount - payments) over invoices not paid or void; overdue = the same with
due_on before today; overall budget ratio = sum of costs / sum of budgets, computed, never typed.
"""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Any, Literal

from fastapi import APIRouter

from app.engine.leakage import STAGE_PROBABILITY
from app.hr import service as hr
from app.platform.context import Ctx, SessionCtx
from app.platform.db import Db, jsonb
from app.platform.errors import denied
from app.platform.permissions import DASHBOARD_FOR_ROLE
from app.platform.responses import ok
from app.platform.serialize import money, to_json
from app.platform.timeutil import utcnow
from app.projects.service import cost_to_date

router = APIRouter(prefix="/api/v1/dashboards")
CACHE_SECONDS = 300
NIL = uuid.UUID(int=0)
OPEN_STAGES = ["new", "qualified", "proposal", "negotiation"]


def tile(key: str, label: str, value: Any, source: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "label": label, "value": value, "source": source, **extra}


def gap(key: str, reason: str) -> dict[str, str]:
    return {"key": key, "reason": reason}


class Metrics:
    """Queries shared by the dashboards. All run under the caller's RLS."""

    def __init__(self, ctx: Ctx, period: str):
        self.ctx, self.db, self.cal, self.now = ctx, ctx.db, ctx.calendar, utcnow()
        self.today = self.cal.local_date(self.now)
        self.base = ctx.org["base_currency"]
        if period == "this_month":
            start = self.today.replace(day=1)
            end = (start + dt.timedelta(days=32)).replace(day=1) - dt.timedelta(days=1)
            self.period = {"label": start.strftime("%B %Y"), "from": start, "to": end}
        else:
            self.period = {"label": "Last 30 days", "from": self.today - dt.timedelta(days=29), "to": self.today}

    # ---------------------------------------------------------------- money
    def invoiced(self) -> Decimal:
        return self.db.scalar("SELECT coalesce(sum(amount), 0) FROM ems.invoices WHERE status <> 'void' AND currency = :c "
                              "AND issued_on BETWEEN :f AND :t", c=self.base, f=self.period["from"], t=self.period["to"])

    def collected(self) -> Decimal:
        return self.db.scalar("SELECT coalesce(sum(p.amount), 0) FROM ems.payments p JOIN ems.invoices i ON i.id = p.invoice_id "
                              "WHERE i.currency = :c AND p.received_on BETWEEN :f AND :t", c=self.base, f=self.period["from"], t=self.period["to"])

    def unpaid(self, overdue_only: bool) -> dict[str, Any]:
        row = self.db.one(
            "SELECT count(*) AS n, coalesce(sum(i.amount - coalesce(p.paid, 0)), 0) AS amount FROM ems.invoices i "
            "LEFT JOIN (SELECT invoice_id, sum(amount) AS paid FROM ems.payments GROUP BY invoice_id) p ON p.invoice_id = i.id "
            "WHERE i.status NOT IN ('paid','void') AND i.currency = :c AND (NOT :od OR i.due_on < :today)",
            c=self.base, od=overdue_only, today=self.today)
        return {"count": row["n"], "amount": row["amount"]}

    def at_risk(self) -> Decimal:
        return self.db.scalar("SELECT coalesce(sum(amount_at_risk), 0) FROM ems.leakage_findings WHERE status = 'open' AND currency = :c",
                              c=self.base)

    def open_findings(self) -> int:
        return self.db.scalar("SELECT count(*) FROM ems.leakage_findings WHERE status = 'open'")

    def pipeline(self) -> tuple[list[dict], Decimal, Decimal]:
        rows = {r["stage"]: r for r in self.db.all("SELECT stage, count(*) AS n, coalesce(sum(amount), 0) AS amount FROM ems.deals "
                                                    "WHERE stage = ANY(:s) AND currency = :c GROUP BY stage", s=OPEN_STAGES, c=self.base)}
        stages = [{"stage": s, "count": rows[s]["n"] if s in rows else 0, "amount": money(rows[s]["amount"] if s in rows else 0)}
                  for s in OPEN_STAGES]
        total = sum((Decimal(r["amount"]) for r in rows.values()), Decimal(0))
        weighted = sum((Decimal(r["amount"]) * STAGE_PROBABILITY[s] for s, r in rows.items()), Decimal(0))
        return stages, total, weighted

    def won(self) -> dict[str, Any]:
        start = self.cal.day_bounds(self.period["from"])[0]
        end = self.cal.day_bounds(self.period["to"])[1]
        row = self.db.one("SELECT count(*) AS n, coalesce(sum(amount), 0) AS amount FROM ems.deals WHERE stage = 'won' AND currency = :c "
                          "AND won_at >= :s AND won_at < :e", c=self.base, s=start, e=end)
        return {"count": row["n"], "amount": row["amount"]}

    def budget_projects(self) -> tuple[list[dict], Decimal | None]:
        rows = self.db.all("SELECT id, name, budget_amount FROM ems.projects WHERE billing_type = 'fixed' AND budget_amount > 0 "
                           "AND status NOT IN ('completed','cancelled') AND currency = :c ORDER BY name", c=self.base)
        costs = cost_to_date(self.db, [r["id"] for r in rows])
        out, total_cost, total_budget = [], Decimal(0), Decimal(0)
        for r in rows:
            c = costs.get(r["id"], {"cost": Decimal(0), "rates_missing": 0})
            total_cost += c["cost"]
            total_budget += r["budget_amount"]
            out.append({"project": r["name"], "budget": money(r["budget_amount"]), "cost_to_date": money(c["cost"]),
                        "ratio": str((c["cost"] / r["budget_amount"]).quantize(Decimal("0.01"))),
                        "entries_without_cost_rate": c["rates_missing"]})
        return out, (total_cost / total_budget).quantize(Decimal("0.01")) if total_budget else None

    def excluded_currencies(self) -> list[str]:
        rows = self.db.all("SELECT currency FROM ems.invoices WHERE currency <> :c UNION SELECT currency FROM ems.deals WHERE currency <> :c",
                           c=self.base)
        return sorted(r["currency"] for r in rows)

    # ---------------------------------------------------------------- people
    def today_people(self) -> dict[str, int]:
        members = [r["user_id"] for r in self.db.all("SELECT user_id FROM ems.memberships WHERE status = 'active'")]
        summaries = hr.day_summaries(self.db, self.cal, members, self.today, self.now)
        leave = hr.approved_leave_on(self.db, self.today)
        counts = {"headcount": len(members), "present": 0, "late": 0, "on_leave": 0, "absent_unexplained": 0, "not_checked_in": 0}
        for u in members:
            status = hr.day_status(self.cal, self.today, self.today, self.now, u in summaries, u in leave)
            if status:
                counts[status] += 1
            if u in summaries and summaries[u]["minutes_late"] > 0:
                counts["late"] += 1
        counts["checked_in_now"] = self.db.scalar("SELECT count(*) FROM ems.work_sessions WHERE state = 'open'")
        return counts

    # ---------------------------------------------------------------- work
    def overdue_tasks(self) -> int:
        return self.db.scalar("SELECT count(*) FROM ems.tasks WHERE status <> 'done' AND due_at < now()")

    def projects_by_status(self, status: str) -> int:
        return self.db.scalar("SELECT count(*) FROM ems.projects WHERE status = :s", s=status)

    def projects_at_risk(self) -> int:
        return self.db.scalar(
            "SELECT count(*) FROM ems.projects p WHERE p.status IN ('planned','active','on_hold') AND ("
            "EXISTS (SELECT 1 FROM ems.leakage_findings f WHERE f.status = 'open' AND f.entity_type = 'project' AND f.entity_id = p.id) "
            "OR EXISTS (SELECT 1 FROM ems.tasks t WHERE t.project_id = p.id AND t.status <> 'done' AND t.due_at < now()))")

    def tasks_done_this_week(self) -> int:
        monday = self.today - dt.timedelta(days=self.today.weekday())
        return self.db.scalar("SELECT count(DISTINCT payload->>'task_id') FROM ems.outbox_events WHERE routing_key = 'task.status_changed' "
                              "AND payload->>'to_status' = 'done' AND created_at >= :s", s=self.cal.day_bounds(monday)[0])

    def rule_stats(self) -> dict[str, int]:
        row = self.db.one("SELECT count(*) AS runs, count(*) FILTER (WHERE outcome = 'action_failed') AS failed FROM ems.rule_runs "
                          "WHERE ran_at > now() - interval '7 days'")
        active = self.db.scalar("SELECT count(*) FROM (SELECT DISTINCT ON (key) enabled FROM ems.rules ORDER BY key, version DESC) r "
                                "WHERE r.enabled")
        return {"runs": row["runs"], "failed": row["failed"], "active": active}


def money_tile(m: Metrics, key: str, label: str, value: Decimal, source: str, **extra) -> dict:
    return tile(key, label, money(value), source, **extra)


def ceo(m: Metrics) -> dict:
    people, (_, total, weighted), won, out = m.today_people(), m.pipeline(), m.won(), m.unpaid(False)
    return {"tiles": [
        tile("checked_in_now", "Checked in now", people["checked_in_now"], "work_sessions"),
        tile("late_today", "Late today", people["late"], "work_sessions + organizations.work_hours"),
        tile("on_leave_today", "On leave today", people["on_leave"], "leave_requests"),
        money_tile(m, "open_pipeline", "Open pipeline", total, "deals", weighted=money(weighted)),
        money_tile(m, "won", "Won this period", won["amount"], "deals", count=won["count"]),
        money_tile(m, "invoiced", "Invoiced", m.invoiced(), "invoices"),
        money_tile(m, "collected", "Collected", m.collected(), "payments"),
        money_tile(m, "outstanding", "Outstanding invoices", out["amount"], "invoices - payments", count=out["count"]),
        money_tile(m, "leakage", "Revenue at risk", m.at_risk(), "leakage_findings"),
        tile("projects_at_risk", "Projects at risk", m.projects_at_risk(), "projects + tasks + leakage_findings")],
        "unavailable": [gap("net_profit", "Needs operating expenses (no accounting integration in Release 1)"),
                        gap("operating_expenses", "No accounting integration in Release 1")]}


def cto(m: Metrics) -> dict:
    rules = m.rule_stats()
    return {"tiles": [
        tile("projects_in_progress", "Projects in progress", m.projects_by_status("active"), "projects"),
        tile("tasks_done_this_week", "Tasks done this week", m.tasks_done_this_week(), "task.status_changed events"),
        tile("overdue_tasks", "Overdue tasks", m.overdue_tasks(), "tasks"),
        tile("rule_runs_7d", "Rule runs (7 days)", rules["runs"], "rule_runs", failed=rules["failed"]),
        tile("active_automations", "Active automations", rules["active"], "rules")],
        "unavailable": [gap(k, "Needs a monitoring or CI integration (Release 2)")
                        for k in ("system_uptime", "open_incidents", "deployments", "latency")]}


def cfo(m: Metrics) -> dict:
    out, overdue = m.unpaid(False), m.unpaid(True)
    projects, overall = m.budget_projects()
    return {"tiles": [
        money_tile(m, "invoiced", "Invoiced", m.invoiced(), "invoices"),
        money_tile(m, "collected", "Collected", m.collected(), "payments"),
        money_tile(m, "outstanding", "Outstanding invoices", out["amount"], "invoices - payments", count=out["count"]),
        money_tile(m, "overdue", "Overdue invoices", overdue["amount"], "invoices - payments", count=overdue["count"]),
        tile("budget_use", "Project budget use", str(overall) if overall is not None else None, "time_entries x cost_rate / budgets"),
        money_tile(m, "leakage", "Revenue at risk", m.at_risk(), "leakage_findings")],
        "budget_projects": projects,
        "unavailable": [gap("operating_expenses", "No accounting integration in Release 1"), gap("net_profit", "Needs operating expenses"),
                        gap("payroll_summary", "Payroll is Release 2"), gap("bills", "No accounting integration in Release 1")]}


def coo(m: Metrics) -> dict:
    people, (stages, _, _) = m.today_people(), m.pipeline()
    expected = people["headcount"] - people["on_leave"]
    rate = (round(100 * people["present"] / expected) if expected else None) if m.cal.is_working_day(m.today) else None
    return {"tiles": [
        tile("attendance_rate", "Attendance today", rate, "work_sessions + leave_requests", unit="percent"),
        tile("active_projects", "Active projects", m.projects_by_status("active"), "projects"),
        tile("overdue_tasks", "Overdue tasks", m.overdue_tasks(), "tasks"),
        tile("pipeline_by_stage", "Pipeline by stage", stages, "deals"),
        tile("open_findings", "Open leakage findings", m.open_findings(), "leakage_findings")],
        "unavailable": [gap("capacity_planning", "Not in Release 1")]}


def hr_dashboard(m: Metrics) -> dict:
    people = m.today_people()
    start, end = m.cal.day_bounds(m.today)
    allowance = m.ctx.org["daily_break_allowance_minutes"]
    overruns = m.db.scalar(
        "SELECT count(*) FROM (SELECT user_id FROM ems.breaks WHERE status IN ('active','ended') AND started_at >= :s AND started_at < :e "
        "GROUP BY user_id HAVING sum(floor(extract(epoch FROM coalesce(ended_at, now()) - started_at) / 60)) > :a) x",
        s=start, e=end, a=allowance)
    idle = m.db.scalar("SELECT count(*) FROM ems.leakage_findings WHERE kind = 'idle_paid_time' AND status = 'open'")
    return {"tiles": [
        tile("headcount", "Headcount", people["headcount"], "memberships"),
        tile("present", "Present today", people["present"], "work_sessions"),
        tile("late", "Late today", people["late"], "work_sessions + organizations.work_hours"),
        tile("absent", "Absent (unexplained)", people["absent_unexplained"], "work_sessions + leave_requests",
             not_checked_in=people["not_checked_in"]),
        tile("pending_leave", "Pending leave requests", m.db.scalar("SELECT count(*) FROM ems.leave_requests WHERE status = 'pending'"),
             "leave_requests"),
        tile("break_overruns", "Break overruns today", overruns, "breaks"),
        tile("idle_above_threshold", "Idle above threshold (to review)", idle, "leakage_findings (idle_paid_time)")],
        "unavailable": [gap("payroll", "Payroll is Release 2")]}


def employee(m: Metrics) -> dict:
    db, me = m.db, m.ctx.user_id
    by_status = {r["status"]: r["n"] for r in db.all("SELECT status, count(*) AS n FROM ems.tasks WHERE assignee_id = :u GROUP BY status", u=me)}
    today = hr.day_summaries(db, m.cal, [me], m.today, m.now).get(me)
    monday = m.today - dt.timedelta(days=m.today.weekday())
    viewers = db.scalar("SELECT count(*) FROM ems.stream_views WHERE subject_user_id = :u AND started_at >= :s",
                        u=me, s=m.cal.day_bounds(monday)[0])
    balance = hr.leave_balances(db, m.cal, me, m.today)
    tiles = [tile("my_tasks", "My tasks", {s: by_status.get(s, 0) for s in ("todo", "active", "review", "done")}, "tasks"),
             tile("my_time_today", "My active time today", today["totals"]["active"] if today else 0, "presence_segments", unit="minutes"),
             tile("viewed_my_screen", "Screen views this week", viewers, "stream_views")]
    unavailable = []
    if balance is None:
        unavailable.append(gap("leave_balance", "No leave policy has been published"))
    else:
        tiles.insert(2, tile("leave_balance", "My leave balance", balance, "hr_policies + leave_requests", unit="days"))
    return {"tiles": tiles, "unavailable": unavailable}


BUILDERS = {"ceo": ceo, "cto": cto, "cfo": cfo, "coo": coo, "hr": hr_dashboard, "employee": employee}


def _cached(db: Db, role: str, period: str, scope_user: uuid.UUID) -> dict | None:
    return db.scalar("SELECT payload FROM ems.dashboard_cache WHERE role = :r AND period = :p AND scope_user = :u "
                     "AND computed_at > now() - make_interval(secs => :ttl)", r=role, p=period, u=scope_user, ttl=CACHE_SECONDS)


@router.get("/{role}")
def dashboard(role: Literal["ceo", "cto", "cfo", "coo", "hr", "employee"], ctx: SessionCtx,
              period: Literal["this_month", "last_30_days"] = "this_month"):
    if not ctx.can("dashboards.all") and DASHBOARD_FOR_ROLE[ctx.role] != role:
        raise denied("You can only open your own role's dashboard.")
    scope_user = ctx.user_id if role == "employee" else NIL     # the employee dashboard is personal
    payload = _cached(ctx.db, role, period, scope_user)
    if payload is None:
        m = Metrics(ctx, period)
        payload = to_json({"role": role, "period": m.period, "currency": m.base, **BUILDERS[role](m)})
        excluded = m.excluded_currencies()
        if excluded:
            payload["notes"] = [f"Amounts in {', '.join(excluded)} are not included; totals are in {m.base}."]
        ctx.db.execute("INSERT INTO ems.dashboard_cache (org_id, role, period, scope_user, payload, computed_at) "
                       "VALUES (:org, :r, :p, :u, CAST(:pl AS jsonb), now()) ON CONFLICT (org_id, role, period, scope_user) "
                       "DO UPDATE SET payload = EXCLUDED.payload, computed_at = EXCLUDED.computed_at",
                       org=ctx.org_id, r=role, p=period, u=scope_user, pl=jsonb(payload))
    return ok(payload)
