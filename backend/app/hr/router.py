"""People, attendance, leave and HR reports (API-029..034)."""
import datetime as dt
import re
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy.exc import IntegrityError

from app.hr import service as hr
from app.platform.context import Ctx, SessionCtx
from app.platform.db import like_pattern
from app.platform.errors import ApiError, denied, invalid, not_found, version_conflict
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.permissions import ALL
from app.platform.responses import ok
from app.platform.schema import Body, ExpectedVersion
from app.platform.timeutil import utcnow

router = APIRouter(prefix="/api/v1")
MAX_ATTENDANCE_DAYS = 62


def _hr_scope_ids(ctx: Ctx, message: str) -> set[uuid.UUID] | None:
    """None = whole company; a set = the manager's team. Raises when the caller has no hr.manage."""
    scope = ctx.scope("hr.manage")
    if scope is None:
        raise denied(message)
    return None if scope == ALL else ctx.team_ids()


# ------------------------------------------------------------------------------------------------ API-029
@router.get("/employees")
def employee_directory(ctx: SessionCtx, department: str | None = None, status: Literal["active", "deactivated"] | None = None,
                       q: str | None = None, cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    team = _hr_scope_ids(ctx, "You can only see your own profile.")
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT m.user_id, u.name, m.title, m.department, m.status, mu.name AS manager FROM ems.memberships m "
        "JOIN ems.users u ON u.id = m.user_id LEFT JOIN ems.users mu ON mu.id = m.manager_id "
        "WHERE (CAST(:dept AS text) IS NULL OR m.department = :dept) AND m.status = coalesce(CAST(:status AS text), 'active') "
        "AND (CAST(:q AS text) IS NULL OR u.name ILIKE :q) "
        "AND (CAST(:team AS uuid[]) IS NULL OR m.user_id = ANY(CAST(:team AS uuid[]))) "
        "AND (CAST(:a_name AS text) IS NULL OR (u.name, m.user_id) > (:a_name, CAST(:a_id AS uuid))) "
        "ORDER BY u.name, m.user_id LIMIT :lim",
        dept=department, status=status, q=like_pattern(q) if q else None, team=list(team) if team is not None else None,
        a_name=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["name"], str(r["user_id"])])
    cal, now = ctx.calendar, utcnow()
    today = cal.local_date(now)
    ids = [r["user_id"] for r in rows]
    days = hr.day_summaries(ctx.db, cal, ids, today, now)
    leave = hr.approved_leave_on(ctx.db, today)
    items = []
    for r in rows:
        d = days.get(r["user_id"])
        if d and d["check_out"] is None:
            state = {"state": "checked_in", "since": d["check_in"], "minutes_late": d["minutes_late"]}
        elif d:
            state = {"state": "checked_out", "since": d["check_out"], "minutes_late": d["minutes_late"]}
        elif r["user_id"] in leave:
            state = {"state": "on_leave", "since": None, "minutes_late": None}
        else:
            state = {"state": "not_checked_in" if cal.is_working_day(today) else "day_off", "since": None, "minutes_late": None}
        items.append({"user_id": r["user_id"], "name": r["name"], "title": r["title"], "department": r["department"],
                      "manager": r["manager"], "status": r["status"], "today": state,
                      "leave_balance_days": hr.leave_balances(ctx.db, cal, r["user_id"], today)})
    return ok({"items": items, "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-030
@router.get("/attendance")
def attendance(ctx: SessionCtx, user_id: uuid.UUID | None = None, from_: Annotated[dt.date | None, Query(alias="from")] = None,
               to: Annotated[dt.date | None, Query()] = None):
    cal, now = ctx.calendar, utcnow()
    today = cal.local_date(now)
    target = user_id or ctx.user_id
    if target != ctx.user_id and not ctx.covers("hr.manage", target):
        raise denied("You can only see your own attendance.")
    if not ctx.db.scalar("SELECT 1 FROM ems.memberships WHERE user_id = :u", u=target):
        raise not_found("Employee")
    to = to or today
    from_ = from_ or to
    if from_ > to or (to - from_).days + 1 > MAX_ATTENDANCE_DAYS:
        raise ApiError("VALIDATION_FAILED", "Choose a range of at most 62 days.")

    days, totals = [], {"present_days": 0, "late_days": 0, "active_minutes": 0}
    day = from_
    while day <= min(to, today):
        summary = hr.day_summaries(ctx.db, cal, [target], day, now).get(target)
        on_leave = target in hr.approved_leave_on(ctx.db, day)
        status = hr.day_status(cal, day, today, now, summary is not None, on_leave)
        if status == "present":
            t = summary["totals"]
            days.append({"date": day, "check_in": cal.local(summary["check_in"]).strftime("%H:%M"),
                         "check_out": cal.local(summary["check_out"]).strftime("%H:%M") if summary["check_out"] else None,
                         "minutes_late": summary["minutes_late"], "active": t["active"], "idle": t["idle"],
                         "locked": t["locked"], "on_break": t["on_break"], "offline": t["offline"], "status": status})
            totals["present_days"] += 1
            totals["late_days"] += 1 if summary["minutes_late"] > 0 else 0
            totals["active_minutes"] += t["active"]
        elif status is not None:
            days.append({"date": day, "status": status})
        day += dt.timedelta(days=1)
    return ok({"user_id": target, "days": days, "totals": totals})


# ------------------------------------------------------------------------------------------------ API-031
class LeaveIn(Body):
    kind: Literal["annual", "sick", "casual", "unpaid"]
    start_date: dt.date
    end_date: dt.date
    reason: str | None = Field(default=None, max_length=500)


@router.post("/leave-requests", status_code=201)
def request_leave(body: LeaveIn, ctx: SessionCtx, idem: IdemKey):
    if body.end_date < body.start_date:
        raise invalid("The leave must end on or after its start date.", {"end_date": "On or after start_date."})
    if (body.end_date - body.start_date).days > 365:
        raise invalid("Request at most one year of leave at a time.", {"end_date": "Too far from start_date."})
    cal = ctx.calendar
    days = cal.working_days(body.start_date, body.end_date)
    if days == 0:
        raise invalid("These dates contain no working days.", {"start_date": "No working days in range."})

    def handler():
        db = ctx.db
        allowances = hr.leave_allowances(db) or {}
        balance_after = {}
        if body.kind in allowances:
            year = body.start_date.year
            approved = hr.leave_days_by_kind(db, cal, ctx.user_id, year, ("approved",)).get(body.kind, 0)
            pending = hr.leave_days_by_kind(db, cal, ctx.user_id, year, ("pending",)).get(body.kind, 0)
            available = allowances[body.kind] - approved - pending
            if days > available:
                raise ApiError("INSUFFICIENT_BALANCE", f"Not enough {body.kind} leave: {max(available, 0)} day(s) available.",
                               {"available_days": max(available, 0), "requested_days": days})
            balance_after = {body.kind: allowances[body.kind] - approved - days}
        request_id = uuid.uuid4()
        try:
            with db.savepoint():
                db.execute("INSERT INTO ems.leave_requests (id, org_id, user_id, kind, period, reason) "
                           "VALUES (:id, :org, :u, :k, daterange(:s, :e, '[]'), :r)",
                           id=request_id, org=ctx.org_id, u=ctx.user_id, k=body.kind, s=body.start_date, e=body.end_date, r=body.reason)
        except IntegrityError as exc:                    # exclusion constraint (DB-08)
            raise ApiError("LEAVE_OVERLAP", "You already have leave requested or approved for part of these dates.") from exc
        approver = hr.approver_for(db, ctx.user_id)
        ctx.audit("leave.requested", "leave_request", request_id)
        ctx.emit("leave.requested", {"request_id": str(request_id), "user_id": str(ctx.user_id), "kind": body.kind, "days": days,
                                     "leave_balance": balance_after.get(body.kind),
                                     "team_on_leave": hr.team_on_leave(db, ctx.user_id, body.start_date, body.end_date)})
        return ok({"request_id": request_id, "status": "pending", "days": days, "approver": approver["label"],
                   "balance_after_approval": balance_after}, f"Leave request sent to {approver['label']}.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-032
@router.get("/leave-requests")
def list_leave(ctx: SessionCtx, status: Literal["pending", "approved", "rejected", "cancelled"] | None = None,
               scope: Literal["mine", "to_decide"] = "mine", cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    if scope == "mine":
        who = "l.user_id = :me"
    elif ctx.role == "ceo":
        who = "l.user_id <> :me"
    elif ctx.role == "hr":
        who = "l.user_id <> :me AND m.role NOT IN ('cto','cfo','coo')"
    elif ctx.role == "manager":
        who = "l.user_id = ANY(CAST(:team AS uuid[])) AND m.role NOT IN ('ceo','cto','cfo','coo')"
    else:
        return ok({"items": [], "next_cursor": None})
    if scope == "to_decide" and status is None:
        status = "pending"
    rows = ctx.db.all(
        "SELECT l.id, l.user_id, u.name, l.kind, lower(l.period) AS start_date, upper(l.period) - 1 AS end_date, l.status, "  # noqa: S608 - only fixed SQL fragments are interpolated
        f"l.version, l.created_at FROM ems.leave_requests l JOIN ems.memberships m ON m.user_id = l.user_id "
        f"JOIN ems.users u ON u.id = l.user_id WHERE {who} AND (CAST(:status AS text) IS NULL OR l.status = :status) "
        "AND (CAST(:a_t AS timestamptz) IS NULL OR (l.created_at, l.id) < (CAST(:a_t AS timestamptz), CAST(:a_id AS uuid))) "
        "ORDER BY l.created_at DESC, l.id DESC LIMIT :lim",
        me=ctx.user_id, team=list(ctx.team_ids()) if ctx.role == "manager" else [], status=status,
        a_t=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["created_at"].isoformat(), str(r["id"])])
    cal = ctx.calendar
    return ok({"items": [{"request_id": r["id"], "employee": r["name"], "kind": r["kind"], "start_date": r["start_date"],
                          "end_date": r["end_date"], "days": cal.working_days(r["start_date"], r["end_date"]), "status": r["status"],
                          "team_on_leave_same_days": hr.team_on_leave(ctx.db, r["user_id"], r["start_date"], r["end_date"]),
                          "version": r["version"]} for r in rows], "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-033
class LeaveDecisionIn(Body):
    expected_version: ExpectedVersion
    decision: Literal["approved", "rejected"]
    note: str | None = Field(default=None, max_length=500)


@router.post("/leave-requests/{request_id}/decision")
def decide_leave(request_id: uuid.UUID, body: LeaveDecisionIn, ctx: SessionCtx):
    db = ctx.db
    lr = db.one("SELECT id, user_id, status, version FROM ems.leave_requests WHERE id = :id FOR UPDATE", id=request_id)
    if lr is None:
        raise not_found("Leave request")
    if lr["user_id"] == ctx.user_id:
        raise denied("You cannot approve your own leave.")
    if not ctx.can("leave.decide") or not hr.can_decide_leave(db, ctx.user_id, ctx.role, ctx.team_ids(), lr["user_id"]):
        raise denied("You cannot decide this leave request.")
    if lr["status"] != "pending":
        raise ApiError("VERSION_CONFLICT", "This request was already decided.", {"current_status": lr["status"]})
    if lr["version"] != body.expected_version:
        raise version_conflict(lr["version"], "This request was changed by someone else. Reload and try again.")
    row = db.one("UPDATE ems.leave_requests SET status = :st, decided_by = :me, decided_at = now(), version = version + 1 "
                 "WHERE id = :id RETURNING status, decided_at, version", st=body.decision, me=ctx.user_id, id=request_id)
    ctx.audit("leave.decided", "leave_request", request_id, ["status", "decided_by"])
    ctx.emit("leave.decided", {"request_id": str(request_id), "user_id": str(lr["user_id"]), "decision": body.decision,
                               "note": body.note})
    decider = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=ctx.user_id)
    return ok({"request_id": request_id, "status": row["status"], "decided_by": decider, "decided_at": row["decided_at"],
               "version": row["version"]})


# ------------------------------------------------------------------------------------------------ API-034
def daily_report(ctx: Ctx, day: dt.date, team: set[uuid.UUID] | None) -> dict:
    db, cal, now = ctx.db, ctx.calendar, utcnow()
    today = cal.local_date(now)
    members = db.all("SELECT m.user_id, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id "
                     "WHERE m.status = 'active' AND (CAST(:team AS uuid[]) IS NULL OR m.user_id = ANY(CAST(:team AS uuid[]))) "
                     "ORDER BY u.name", team=list(team) if team is not None else None)
    ids = [m["user_id"] for m in members]
    summaries = hr.day_summaries(db, cal, ids, day, now)
    leave = hr.approved_leave_on(db, day)
    start, end = cal.day_bounds(day)
    breaks = {r["user_id"]: int(r["minutes"]) for r in db.all(
        "SELECT user_id, sum(floor(extract(epoch FROM coalesce(ended_at, least(now(), :e)) - started_at) / 60)) AS minutes "
        "FROM ems.breaks WHERE user_id = ANY(:ids) AND started_at >= :s AND started_at < :e AND status IN ('active','ended') "
        "GROUP BY user_id", ids=ids, s=start, e=end)}
    allowance = ctx.org["daily_break_allowance_minutes"]
    counts = {"present": 0, "on_leave": 0, "absent_unexplained": 0, "not_checked_in": 0}
    late, idle, over, active_total = [], [], [], 0
    for m in members:
        s = summaries.get(m["user_id"])
        status = hr.day_status(cal, day, today, now, s is not None, m["user_id"] in leave)
        if status:
            counts[status] += 1
        if s:
            active_total += s["totals"]["active"]
            if s["minutes_late"] > 0:
                late.append({"name": m["name"], "minutes": s["minutes_late"]})
            if s["totals"]["idle"] > hr.IDLE_REVIEW_THRESHOLD:
                idle.append({"name": m["name"], "idle_minutes": s["totals"]["idle"]})
        if breaks.get(m["user_id"], 0) > allowance:
            over.append({"name": m["name"], "minutes_over": breaks[m["user_id"]] - allowance})
    return {"date": day, "headcount": len(members), "present": counts["present"], "on_leave": counts["on_leave"],
            "absent_unexplained": counts["absent_unexplained"], "not_checked_in": counts["not_checked_in"], "late": late,
            "idle_over_threshold": idle, "break_over_allowance": over, "active_minutes_total": active_total,
            "notes": "Idle time is a review signal, not a performance score."}


@router.get("/hr/reports/daily")
def hr_report(ctx: SessionCtx, date: dt.date | None = None, week: str | None = None):
    team = _hr_scope_ids(ctx, "Only HR and leadership can view company reports.")
    if date and week:
        raise invalid("Send either date or week, not both.")
    if week:
        m = re.fullmatch(r"(\d{4})-W(\d{2})", week)
        if not m:
            raise invalid("Use an ISO week such as 2026-W42.", {"week": "Format YYYY-Www."})
        try:
            monday = dt.date.fromisocalendar(int(m.group(1)), int(m.group(2)), 1)
        except ValueError as exc:
            raise invalid("That week does not exist.", {"week": "Invalid week number."}) from exc
        today = ctx.calendar.local_date()
        days = [daily_report(ctx, monday + dt.timedelta(days=i), team) for i in range(7) if monday + dt.timedelta(days=i) <= today]
        return ok({"week": week, "days": days,
                   "totals": {k: sum(d[k] for d in days) for k in ("present", "on_leave", "absent_unexplained", "active_minutes_total")}})
    return ok(daily_report(ctx, date or ctx.calendar.local_date(), team))
