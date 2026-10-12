"""HR Agent and HR policies (API-035..037, spec Section 11, TASK-008).

The agent is `engine/hr_agent.py`: ordered patterns pick one intent, the intent runs a fixed query through the `Repo`
interface, and the answer is a template filled with real records plus the IDs it used. No language model (OD-06).
`SqlRepo` below implements that interface under the caller's RLS. A manager's view is limited to their direct reports
(the "team only" scope of Section 7.2); only the intent is logged (`agent_logs`), never the question text.
"""
import datetime as dt
import re
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Path, Request
from pydantic import Field
from sqlalchemy.exc import IntegrityError

from app.engine import hr_agent
from app.hr import service as hr
from app.platform import ratelimit
from app.platform.context import Ctx, SessionCtx
from app.platform.db import jsonb
from app.platform.errors import denied, invalid, version_conflict
from app.platform.permissions import ALL
from app.platform.responses import ok
from app.platform.schema import Body, ExpectedVersion
from app.platform.timeutil import utcnow
from app.room import service as room

router = APIRouter(prefix="/api/v1/hr-agent")

TOPICS = ("leave", "attendance", "breaks", "general", "monitoring")
# Machine rules each policy topic may carry (Section 10 allowances and grace). Anything else is rejected, so the
# Room, leave balances and the agent never read a value nobody validated.
POLICY_RULES: dict[str, dict[str, tuple[int, int]]] = {
    "leave": {f"{k}_days": (0, 365) for k in hr.LEAVE_KINDS},
    "attendance": {"late_grace_minutes": (0, 120), "daily_break_allowance_minutes": (0, 240)},
    "breaks": {"daily_break_allowance_minutes": (0, 240)},
    "general": {},
    "monitoring": {},
}


class SqlRepo(hr_agent.Repo):
    """engine/hr_agent.py Repo over PostgreSQL. `team` is None for company-wide callers, else the visible user IDs."""

    def __init__(self, ctx: Ctx, team: set[uuid.UUID] | None):
        self.ctx, self.db, self.cal, self.now = ctx, ctx.db, ctx.calendar, utcnow()
        self.team = team

    def _visible(self, user_id: uuid.UUID) -> bool:
        return self.team is None or user_id in self.team

    def leave_on(self, day: dt.date) -> list[dict[str, Any]]:
        rows = self.db.all("SELECT l.id AS request_id, l.user_id, u.name, l.kind FROM ems.leave_requests l JOIN ems.users u ON u.id = l.user_id "
                           "WHERE l.status = 'approved' AND l.period @> CAST(:d AS date) ORDER BY u.name", d=day)
        return [{"user_id": r["user_id"], "name": r["name"], "kind": r["kind"], "request_id": r["request_id"]}
                for r in rows if self._visible(r["user_id"])]

    def pending_leave(self) -> list[dict[str, Any]]:
        rows = self.db.all("SELECT l.id AS request_id, l.user_id, u.name, l.kind, lower(l.period) AS s, upper(l.period) - 1 AS e "
                           "FROM ems.leave_requests l JOIN ems.users u ON u.id = l.user_id WHERE l.status = 'pending' "
                           "ORDER BY lower(l.period), u.name")
        return [{"request_id": r["request_id"], "name": r["name"], "days": self.cal.working_days(r["s"], r["e"]), "kind": r["kind"]}
                for r in rows if self._visible(r["user_id"])]

    def late_on(self, day: dt.date, grace_minutes: int) -> list[dict[str, Any]]:
        """Lateness of each person's first session of the day (the company calendar applies the grace period)."""
        start, end = self.cal.day_bounds(day)
        rows = self.db.all("SELECT DISTINCT ON (s.user_id) s.id, s.user_id, s.started_at, u.name FROM ems.work_sessions s "
                           "JOIN ems.users u ON u.id = s.user_id WHERE s.started_at >= :s AND s.started_at < :e "
                           "ORDER BY s.user_id, s.started_at", s=start, e=end)
        out = [{"user_id": r["user_id"], "name": r["name"], "minutes_late": self.cal.minutes_late(r["started_at"]), "session_id": r["id"]}
               for r in rows if self._visible(r["user_id"])]
        return sorted([r for r in out if r["minutes_late"] > 0], key=lambda r: r["name"])

    def online_now(self) -> list[dict[str, Any]]:
        rows = self.db.all("SELECT s.user_id, s.presence, s.last_heartbeat_at, s.started_at, u.name, t.title FROM ems.work_sessions s "
                           "JOIN ems.users u ON u.id = s.user_id LEFT JOIN ems.tasks t ON t.id = s.current_task_id "
                           "WHERE s.state = 'open' ORDER BY u.name")
        out = []
        for r in rows:
            silent = self.now - (r["last_heartbeat_at"] or r["started_at"]) > room.OFFLINE_AFTER
            if self._visible(r["user_id"]) and r["presence"] != "offline" and not silent:
                out.append({"user_id": r["user_id"], "name": r["name"], "presence": r["presence"], "task": r["title"]})
        return out

    def day_totals(self, user_id: uuid.UUID, day: dt.date) -> dict[str, Any] | None:
        summary = hr.day_summaries(self.db, self.cal, [user_id], day, self.now).get(user_id)
        if summary is None:
            return None
        by_task: dict[Any, float] = {}
        for s in summary["segments"]:
            if s["presence"] == "active" and s["task_id"]:
                by_task[s["task_id"]] = by_task.get(s["task_id"], 0.0) + (s["ended_at"] - s["started_at"]).total_seconds()
        titles = {}
        if by_task:
            titles = {r["id"]: r["title"] for r in self.db.all("SELECT id, title FROM ems.tasks WHERE id = ANY(:ids)", ids=list(by_task))}
        tasks = [{"title": titles.get(t, "Deleted task"), "minutes": int(sec // 60)} for t, sec in by_task.items() if sec >= 60]
        return {**{k: summary["totals"][k] for k in ("active", "idle", "on_break")}, "tasks": sorted(tasks, key=lambda x: -x["minutes"]),
                "session_ids": summary["session_ids"]}

    def find_person(self, text: str) -> dict[str, Any] | None:
        """The member named in the question: full name first, then a unique first name. Ambiguous -> None (never guessed)."""
        members = [m for m in self.db.all("SELECT m.user_id, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id "
                                          "WHERE m.status = 'active'")
                   if self._visible(m["user_id"]) or m["user_id"] == self.ctx.user_id]
        q = text.lower()

        def said(word: str) -> bool:
            return bool(re.search(rf"\b{re.escape(word.lower())}\b", q))
        for pick in (lambda m: m["name"], lambda m: m["name"].split(" ", 1)[0]):
            hits = {m["user_id"]: m for m in members if m["name"] and said(pick(m))}
            if len(hits) == 1:
                m = next(iter(hits.values()))
                return {"user_id": m["user_id"], "name": m["name"]}
            if len(hits) > 1:
                return None
        return None

    def policy(self, topic: str) -> dict[str, Any] | None:
        p = hr.latest_policy(self.db, topic)
        return {"topic": p["topic"], "text": p["text"], "version": p["version"]} if p else None


# ------------------------------------------------------------------------------------------------ API-035
class AskIn(Body):
    question: str = Field(min_length=3, max_length=300)


@router.post("/ask")
def ask(body: AskIn, request: Request, ctx: SessionCtx):
    ratelimit.hit(request.app.state.engine, "hr_agent", str(ctx.user_id))
    scope = ctx.scope("hr.manage")
    team = None if scope == ALL or ctx.role in hr_agent.PRIVILEGED else ctx.team_ids()
    grace = int(ctx.org["work_hours"].get("late_grace_minutes", 0))
    result = hr_agent.answer(body.question, {"user_id": ctx.user_id, "role": ctx.role}, SqlRepo(ctx, team), ctx.calendar.local_date(),
                             grace_minutes=grace)
    ctx.db.execute("INSERT INTO ems.agent_logs (id, org_id, asker_id, intent, answered) VALUES (:id, :org, :u, :i, :a)",
                   id=uuid.uuid4(), org=ctx.org_id, u=ctx.user_id, i=result["intent"], a=result["answered"])
    return ok(result)


# ------------------------------------------------------------------------------------------------ API-036
@router.get("/policies")
def list_policies(ctx: SessionCtx):
    rows = ctx.db.all("SELECT DISTINCT ON (topic) topic, version, text, published_at FROM ems.hr_policies ORDER BY topic, version DESC")
    order = {t: i for i, t in enumerate(TOPICS)}
    return ok({"items": sorted(rows, key=lambda r: order.get(r["topic"], len(order)))})


# ------------------------------------------------------------------------------------------------ API-037
class PolicyIn(Body):
    expected_version: ExpectedVersion                    # the current version; 0 when the topic has never been published
    text: str = Field(min_length=10, max_length=5000)
    rules: dict[str, int] = Field(default_factory=dict)


@router.put("/policies/{topic}")
def publish_policy(topic: Annotated[Literal["leave", "attendance", "breaks", "general", "monitoring"], Path()], body: PolicyIn,
                   ctx: SessionCtx):
    if ctx.scope("hr.manage") != ALL:
        raise denied("Only HR and leadership can publish company policies.")
    allowed = POLICY_RULES[topic]
    bad = {f"rules.{k}": (f"Allowed for {topic}: {', '.join(allowed) or 'none'}." if k not in allowed
                          else f"{allowed[k][0]} to {allowed[k][1]}.")
           for k, v in body.rules.items() if k not in allowed or not allowed[k][0] <= v <= allowed[k][1]}
    if bad:
        raise invalid("Check the policy rules.", bad)
    db = ctx.db
    db.execute("SELECT pg_advisory_xact_lock(hashtext(CAST(:org AS text) || :name))", org=str(ctx.org_id), name=f":policy:{topic}")
    current = db.scalar("SELECT coalesce(max(version), 0) FROM ems.hr_policies WHERE topic = :t", t=topic)
    if current != body.expected_version:
        raise version_conflict(current, "Someone published a newer version. Reload first.")
    version = current + 1
    try:
        with db.savepoint():
            published_at = db.scalar("INSERT INTO ems.hr_policies (org_id, topic, version, text, rules, published_by) "
                                     "VALUES (:org, :t, :v, :text, CAST(:rules AS jsonb), :u) RETURNING published_at",
                                     org=ctx.org_id, t=topic, v=version, text=body.text, rules=jsonb(body.rules), u=ctx.user_id)
    except IntegrityError as exc:                         # policies are insert-only (DB-18); a concurrent publish won
        raise version_conflict(current + 1, "Someone published a newer version. Reload first.") from exc
    _apply_rules(ctx, topic, body.rules)
    ctx.audit("policy.published", "hr_policy", None, ["version", "text", "rules"])
    ctx.emit("policy.published", {"topic": topic, "version": version})
    return ok({"topic": topic, "version": version, "published_at": published_at}, f"{topic.capitalize()} policy v{version} published.")


def _apply_rules(ctx: Ctx, topic: str, rules: dict[str, int]) -> None:
    """Company settings the policy governs. A new monitoring notice needs fresh consent (Section 31.2)."""
    db = ctx.db
    if "late_grace_minutes" in rules:
        db.execute("UPDATE ems.organizations SET work_hours = jsonb_set(work_hours, '{late_grace_minutes}', to_jsonb(CAST(:g AS integer))), "
                   "version = version + 1", g=rules["late_grace_minutes"])
    if "daily_break_allowance_minutes" in rules:
        db.execute("UPDATE ems.organizations SET daily_break_allowance_minutes = :m, version = version + 1",
                   m=rules["daily_break_allowance_minutes"])
    if topic == "monitoring":
        db.execute("UPDATE ems.organizations SET room_policy_version = room_policy_version + 1, version = version + 1")
