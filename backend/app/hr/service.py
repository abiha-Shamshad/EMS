"""Attendance, leave balances and approver routing (spec Section 10)."""
import datetime as dt
import uuid
from typing import Any

from app.platform.db import Db
from app.platform.permissions import LEADERSHIP
from app.platform.timeutil import Calendar
from app.room import service as room

LEAVE_KINDS = ("annual", "sick", "casual", "unpaid")
IDLE_REVIEW_THRESHOLD = 60          # minutes; same default as engine/leakage.py idle_minutes_threshold


def role_holders(db: Db, *roles: str) -> list[uuid.UUID]:
    """Active members holding any of the roles (notification recipients)."""
    return [r["user_id"] for r in db.all("SELECT user_id FROM ems.memberships WHERE status = 'active' AND role = ANY(:r)", r=list(roles))]


def latest_policy(db: Db, topic: str) -> dict[str, Any] | None:
    return db.one("SELECT topic, version, text, rules, published_at FROM ems.hr_policies WHERE topic = :t "
                  "ORDER BY version DESC LIMIT 1", t=topic)


def leave_allowances(db: Db) -> dict[str, int] | None:
    """Per-kind yearly allowance from the published leave policy rules, e.g. {"annual_days": 18} -> {"annual": 18}.
    None when no leave policy is published: balances are then unavailable, never guessed."""
    policy = latest_policy(db, "leave")
    if policy is None:
        return None
    rules = policy["rules"] or {}
    return {k: int(rules[f"{k}_days"]) for k in LEAVE_KINDS if isinstance(rules.get(f"{k}_days"), int)}


def leave_days_by_kind(db: Db, cal: Calendar, user_id: uuid.UUID, year: int, statuses: tuple[str, ...]) -> dict[str, int]:
    """Working days of leave in a calendar year, clipped to the year, per kind."""
    y_start, y_end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    out: dict[str, int] = {}
    for r in db.all("SELECT kind, lower(period) AS s, upper(period) - 1 AS e FROM ems.leave_requests "
                    "WHERE user_id = :u AND status = ANY(:st) AND period && daterange(:ys, :ye, '[]')",
                    u=user_id, st=list(statuses), ys=y_start, ye=y_end):
        out[r["kind"]] = out.get(r["kind"], 0) + cal.working_days(max(r["s"], y_start), min(r["e"], y_end))
    return out


def leave_balances(db: Db, cal: Calendar, user_id: uuid.UUID, today: dt.date) -> dict[str, int] | None:
    allowances = leave_allowances(db)
    if allowances is None:
        return None
    taken = leave_days_by_kind(db, cal, user_id, today.year, ("approved",))
    return {k: allowance - taken.get(k, 0) for k, allowance in allowances.items()}


def approver_for(db: Db, user_id: uuid.UUID) -> dict[str, Any]:
    """Manager if set; leadership roles go to the CEO; otherwise HR (Section 10). The CEO's own leave goes to HR.
    Returns {"user_ids": [...], "label": str}."""
    m = db.one("SELECT m.role, m.manager_id, mm.role AS manager_role, mu.name AS manager_name FROM ems.memberships m "
               "LEFT JOIN ems.memberships mm ON mm.user_id = m.manager_id AND mm.status = 'active' "
               "LEFT JOIN ems.users mu ON mu.id = mm.user_id WHERE m.user_id = :u", u=user_id)
    ceo = db.one("SELECT m.user_id, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id "
                 "WHERE m.role = 'ceo' AND m.status = 'active'")
    if m["role"] in LEADERSHIP - {"ceo"} and ceo:
        return {"user_ids": [ceo["user_id"]], "label": ceo["name"]}
    # Only a manager whose role holds leave.decide (Section 7.2) can be the approver.
    if m["manager_id"] and m["manager_name"] and m["role"] not in LEADERSHIP and m["manager_role"] in ("manager", "hr", "ceo"):
        return {"user_ids": [m["manager_id"]], "label": m["manager_name"]}
    hr = [r for r in db.all("SELECT m.user_id, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id "
                            "WHERE m.role = 'hr' AND m.status = 'active' ORDER BY u.name") if r["user_id"] != user_id]
    if hr:
        return {"user_ids": [r["user_id"] for r in hr], "label": hr[0]["name"] if len(hr) == 1 else "HR"}
    if ceo and ceo["user_id"] != user_id:
        return {"user_ids": [ceo["user_id"]], "label": ceo["name"]}
    return {"user_ids": [], "label": "No approver available"}


def can_decide_leave(db: Db, decider_id: uuid.UUID, decider_role: str, decider_team: set[uuid.UUID], requester_id: uuid.UUID) -> bool:
    """Nobody approves their own leave; leadership requests are decided by the CEO; managers decide for their team."""
    if decider_id == requester_id:
        return False
    requester_role = db.scalar("SELECT role FROM ems.memberships WHERE user_id = :u", u=requester_id)
    if requester_role in LEADERSHIP - {"ceo"}:
        return decider_role == "ceo"
    if requester_role == "ceo":
        return decider_role == "hr"
    if decider_role in ("ceo", "hr"):
        return True
    return decider_role == "manager" and requester_id in decider_team


def team_on_leave(db: Db, user_id: uuid.UUID, start: dt.date, end: dt.date) -> int:
    """Teammates (same department, or same manager when no department) with approved leave overlapping the dates."""
    return int(db.scalar(
        "SELECT count(DISTINCT l.user_id) FROM ems.leave_requests l JOIN ems.memberships t ON t.user_id = l.user_id "
        "JOIN ems.memberships me ON me.user_id = :u "
        "WHERE l.user_id <> :u AND l.status = 'approved' AND l.period && daterange(:s, :e, '[]') AND t.status = 'active' "
        "AND ((me.department IS NOT NULL AND t.department = me.department) "
        "  OR (me.department IS NULL AND me.manager_id IS NOT NULL AND t.manager_id = me.manager_id))",
        u=user_id, s=start, e=end))


def day_summaries(db: Db, cal: Calendar, user_ids: list[uuid.UUID], day: dt.date, now: dt.datetime) -> dict[uuid.UUID, dict]:
    """Per user: first check-in, last check-out, lateness and presence minutes for sessions started that local day."""
    start, end = cal.day_bounds(day)
    sessions = db.all(f"SELECT {room.SESSION_COLUMNS} FROM ems.work_sessions "  # noqa: S608 - constant column list
                      "WHERE user_id = ANY(:u) AND started_at >= :s AND started_at < :e ORDER BY started_at",
                      u=user_ids, s=start, e=end)
    out: dict[uuid.UUID, dict] = {}
    for s in sessions:
        d = out.setdefault(s["user_id"], {"sessions": [], "segments": []})
        d["sessions"].append(s)
        d["segments"] += room.live_segments(db, s, now)
    for d in out.values():
        first, last = d["sessions"][0], d["sessions"][-1]
        d["check_in"] = first["started_at"]
        d["check_out"] = last["ended_at"] if last["state"] != "open" else None
        d["minutes_late"] = cal.minutes_late(first["started_at"])
        d["totals"] = room.totals(d["segments"])
        d["session_ids"] = [s["id"] for s in d["sessions"]]
    return out


def approved_leave_on(db: Db, day: dt.date) -> dict[uuid.UUID, dict]:
    return {r["user_id"]: r for r in db.all(
        "SELECT id, user_id, kind FROM ems.leave_requests WHERE status = 'approved' AND period @> CAST(:d AS date)", d=day)}


def day_status(cal: Calendar, day: dt.date, today: dt.date, now: dt.datetime, has_session: bool, on_leave: bool) -> str | None:
    """present | on_leave | absent_unexplained | not_checked_in (Section 10). None for a non-working day without a session."""
    if has_session:
        return "present"
    if on_leave:
        return "on_leave"
    if not cal.is_working_day(day):
        return None
    if day == today and now < cal.work_end(day):
        return "not_checked_in"
    return "absent_unexplained"
