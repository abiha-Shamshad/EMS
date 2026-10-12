"""Rule engine service (spec Section 15, TASK-013): store rules, run `engine/rules.py` on domain events, execute actions
through module services, record `rule_runs`. No code, regular expressions, URLs or external API calls.

`engine/rules.py` checks triggers, facts, operators and action names. This module adds what the engine leaves to the
service: each action's parameters (who to notify, which task to create) are validated when the rule is saved, so a
saved rule can always be executed.

A run is recorded once per (rule, event) (DB-12) and the rule_runs row is insert-only, so the outcome is decided before
it is written. Actions run in a savepoint: a failing action rolls back that rule's actions only and is recorded as
`action_failed`. Events created by actions carry `chain_depth` + 1; at depth 3 a run is `skipped_loop`.
"""
import datetime as dt
import logging
import uuid
from decimal import Decimal
from typing import Any

from app.engine import rules as engine
from app.engine.leakage import STAGE_PROBABILITY
from app.hr.service import approver_for, role_holders
from app.platform import events
from app.platform.db import Db, jsonb
from app.platform.timeutil import Calendar, utcnow

log = logging.getLogger("ems.rules")

MAX_CHAIN_DEPTH = 3
ACTION_PARAMS = {"notify": {"to", "template", "title"}, "escalate": {"to", "template", "title"},
                 "create_task": {"assign", "title", "due_in_hours"}, "assign_owner": {"to"}, "set_stage_flag": {"flag"},
                 "create_finding": {"kind"}}
# Recipients any rule can name (role holders), and those each trigger's events can resolve (the people it is about).
ROLE_RECIPIENTS = {"hr", "ceo", "coo", "cfo", "leadership"}
TRIGGER_RECIPIENTS = {
    "deal.stale": {"owner"},
    "task.overdue": {"project_owner", "employee"},
    "attendance.late": {"employee", "manager"},
    "invoice.overdue": {"project_owner"},
    "leave.requested": {"employee", "manager", "approver"},
    "prospect.scored": {"hunt_owner"},
}
NOTIFY_TEMPLATES = {
    "deal_stale": "No activity on {deal.title} for {deal.days_since_activity} days",
    "task_overdue": "{task.title} is {task.hours_overdue} h overdue",
    "late_three_times": "{employee.name} was late {employee.late_count_7d} times in the last 7 days",
    "invoice_overdue": "Invoice {invoice.number} is {invoice.days_overdue} days overdue",
    "leave_team_overlap": "{employee.name} asked for leave while {team.on_leave_count} teammates are already on leave",
    "prospect_high_score": "{prospect.company_name} scored {prospect.score} in the Lead Hunter",
}
SET_FLAGS = {"invoice.overdue": {"at_risk"}}                       # client status the rule may set
FINDING_KINDS = {"deal.stale": "stale_deal", "invoice.overdue": "overdue_invoice"}
OWNER_ENTITIES = {"deal.stale": "deal", "task.overdue": "task"}      # assign_owner: whose owner changes


def _check(cond: bool, reason: str) -> None:
    if not cond:
        raise engine.RuleError(reason)


def validate(defn: dict[str, Any]) -> None:
    """engine/rules.py validation plus action parameters. Raises engine.RuleError with a reason code (RULE_INVALID)."""
    engine.validate(defn)
    trigger = defn["trigger"]
    for i, a in enumerate(defn["then"]):
        name, params = a["action"], {k: v for k, v in a.items() if k != "action"}
        allowed = ACTION_PARAMS[name]
        _check(set(params) <= allowed, f"ACTION_PARAM_UNKNOWN:{i}:{','.join(sorted(set(params) - allowed))}")
        for key in ("to", "assign"):
            if key in allowed and key in params:
                who = params[key]
                _check(who in ROLE_RECIPIENTS or who in TRIGGER_RECIPIENTS[trigger], f"RECIPIENT_NOT_ALLOWED:{who}")
        if name in ("notify", "escalate"):
            _check("to" in params, f"ACTION_PARAM_MISSING:{i}:to")
            _check(("template" in params) != ("title" in params), f"ACTION_PARAM_MISSING:{i}:template_or_title")
            _check("template" not in params or params["template"] in NOTIFY_TEMPLATES, f"TEMPLATE_UNKNOWN:{params.get('template')}")
        if "title" in params:
            _check(isinstance(params["title"], str) and 1 <= len(params["title"]) <= 200, f"TITLE_INVALID:{i}")
        if name == "create_task":
            _check({"assign", "title"} <= set(params), f"ACTION_PARAM_MISSING:{i}:assign_or_title")
            due = params.get("due_in_hours", 24)
            _check(isinstance(due, int) and not isinstance(due, bool) and 1 <= due <= 720, f"DUE_INVALID:{i}")
        if name == "assign_owner":
            _check(trigger in OWNER_ENTITIES and "to" in params, f"ACTION_NOT_FOR_TRIGGER:assign_owner:{trigger}")
        if name == "set_stage_flag":
            _check(params.get("flag") in SET_FLAGS.get(trigger, set()), f"FLAG_NOT_ALLOWED:{params.get('flag')}")
        if name == "create_finding":
            _check(FINDING_KINDS.get(trigger) == params.get("kind"), f"FINDING_NOT_FOR_TRIGGER:{params.get('kind')}")


# ------------------------------------------------------------------------------------------------ facts per event
def _manager_of(db: Db, user_id: Any) -> uuid.UUID | None:
    return db.scalar("SELECT manager_id FROM ems.memberships WHERE user_id = :u AND status = 'active'", u=user_id)


def context_for(db: Db, trigger: str, payload: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """(facts, people/entities) for an event, or None when the event does not apply (e.g. an on-time check-in)."""
    if trigger == "attendance.late":
        if not payload.get("minutes_late"):
            return None
        user_id = payload["user_id"]
        m = db.one("SELECT m.role, m.department, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id WHERE m.user_id = :u",
                   u=user_id)
        org = db.one("SELECT time_zone, work_hours FROM ems.organizations")
        cal, now = Calendar(org["time_zone"], org["work_hours"]), utcnow()
        since = cal.day_bounds(cal.local_date(now) - dt.timedelta(days=6))[0]
        firsts = db.all("SELECT DISTINCT ON (date_trunc('day', started_at AT TIME ZONE :tz)) started_at FROM ems.work_sessions "
                        "WHERE user_id = :u AND started_at >= :s ORDER BY date_trunc('day', started_at AT TIME ZONE :tz), started_at",
                        u=user_id, s=since, tz=org["time_zone"])
        facts = {"employee.minutes_late": payload["minutes_late"], "employee.role": m["role"], "employee.department": m["department"],
                 "employee.late_count_7d": sum(1 for r in firsts if cal.minutes_late(r["started_at"]) > 0),
                 "day.is_holiday": not cal.is_working_day(cal.local_date(now)), "employee.name": m["name"]}
        return facts, {"employee": user_id, "manager": _manager_of(db, user_id), "entity": ("employee", user_id)}
    if trigger == "task.overdue":
        assignee = db.scalar("SELECT assignee_id FROM ems.tasks WHERE id = :t", t=payload["task_id"])
        facts = {k: payload.get(k) for k in ("task.hours_overdue", "task.status", "task.billable", "project.billing_type", "task.title")}
        return facts, {"project_owner": payload.get("project_owner_id"), "employee": assignee, "project_id": payload.get("project_id"),
                       "entity": ("task", payload["task_id"])}
    if trigger == "leave.requested":
        user_id = payload["user_id"]
        name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=user_id)
        facts = {"leave.days": payload.get("days"), "leave.kind": payload.get("kind"), "employee.leave_balance": payload.get("leave_balance"),
                 "team.on_leave_count": payload.get("team_on_leave", 0), "employee.name": name}
        approvers = approver_for(db, uuid.UUID(str(user_id)))["user_ids"]
        return facts, {"employee": user_id, "manager": _manager_of(db, user_id), "approver": approvers,
                       "entity": ("leave_request", payload.get("request_id"))}
    if trigger == "prospect.scored":
        facts = {k: payload.get(k) for k in ("prospect.score", "prospect.has_public_email", "prospect.country")}
        facts["prospect.company_name"] = payload.get("company_name")
        return facts, {"hunt_owner": payload.get("hunt_owner_id"), "entity": ("prospect", payload.get("prospect_id"))}
    if trigger in ("deal.stale", "invoice.overdue"):                 # emitted by the nightly job with facts in the payload
        facts = {k: v for k, v in payload.items() if "." in k}
        people = {k: payload.get(k + "_id") for k in ("owner", "project_owner")}
        return facts, {**people, "entity": (payload["entity_type"], payload["entity_id"]), "client_id": payload.get("client_id")}
    return None


# ------------------------------------------------------------------------------------------------ actions
def _resolve(db: Db, who: str, people: dict[str, Any]) -> list[uuid.UUID]:
    if who in ROLE_RECIPIENTS:
        return role_holders(db, "ceo", "cfo", "coo", "cto") if who == "leadership" else role_holders(db, who)
    value = people.get(who)
    values = value if isinstance(value, list) else [value]
    return [uuid.UUID(str(v)) for v in values if v]


def _followups_project(db: Db, org_id: uuid.UUID, owner: uuid.UUID) -> uuid.UUID:
    """Rule-created tasks that belong to no project (deal follow-ups) go to one internal project per company."""
    db.execute("SELECT pg_advisory_xact_lock(hashtext(CAST(:org AS text) || :name))", org=str(org_id), name=":followups")
    pid = db.scalar("SELECT id FROM ems.projects WHERE name = 'Automation follow-ups' AND billing_type = 'internal' "
                    "AND status NOT IN ('completed','cancelled') ORDER BY created_at LIMIT 1")
    if pid is None:
        pid = uuid.uuid4()
        db.execute("INSERT INTO ems.projects (id, org_id, name, billing_type, owner_id) VALUES (:id, :org, 'Automation follow-ups', 'internal', :o)",
                   id=pid, org=org_id, o=owner)
    return pid


class ActionFailed(Exception):
    pass


def execute(db: Db, org_id: uuid.UUID, rule: dict, event_id: uuid.UUID, action: dict[str, Any], facts: dict[str, Any],
            people: dict[str, Any], depth: int) -> None:
    name = action["action"]
    if name in ("notify", "escalate"):
        recipients = _resolve(db, action["to"], people)
        if not recipients:
            raise ActionFailed(f"no recipient for '{action['to']}'")
        title = engine.render(action.get("title") or NOTIFY_TEMPLATES[action["template"]], facts)
        events.notify(db, org_id, recipients, f"rule.{rule['key']}", ("Escalation: " if name == "escalate" else "") + title,
                      people["entity"][0], people["entity"][1])
    elif name == "create_task":
        assignees = _resolve(db, action["assign"], people)
        if not assignees:
            raise ActionFailed(f"no assignee for '{action['assign']}'")
        project_id = people.get("project_id") or _followups_project(db, org_id, assignees[0])
        task_id = uuid.uuid4()
        position = db.scalar("SELECT coalesce(max(position), 0) + 1 FROM ems.tasks WHERE project_id = :p AND status = 'todo'", p=project_id)
        db.execute("INSERT INTO ems.tasks (id, org_id, project_id, title, assignee_id, due_at, billable, position) "
                   "VALUES (:id, :org, :p, :t, :a, :d, false, :pos)",
                   id=task_id, org=org_id, p=project_id, t=engine.render(action["title"], facts)[:200], a=assignees[0],
                   d=utcnow() + dt.timedelta(hours=action.get("due_in_hours", 24)), pos=position)
        events.emit(db, org_id, "task.created", {"task_id": str(task_id), "project_id": str(project_id), "assignee_id": str(assignees[0]),
                                                 "rule_id": str(rule["id"]), "chain_depth": depth + 1})
    elif name == "assign_owner":
        owners = _resolve(db, action["to"], people)
        if not owners:
            raise ActionFailed(f"no owner for '{action['to']}'")
        kind, entity_id = people["entity"]
        if kind == "deal":
            db.execute("UPDATE ems.deals SET owner_id = :o, version = version + 1 WHERE id = :d", o=owners[0], d=entity_id)
        else:
            db.execute("UPDATE ems.tasks SET assignee_id = :o, version = version + 1 WHERE id = :t", o=owners[0], t=entity_id)
    elif name == "set_stage_flag":
        if not people.get("client_id"):
            raise ActionFailed("the invoice has no client")
        db.execute("UPDATE ems.clients SET status = :f WHERE id = :c AND status <> 'churned'", f=action["flag"], c=people["client_id"])
    elif name == "create_finding":
        kind, entity_id = people["entity"]
        if action["kind"] == "stale_deal":
            amount = Decimal(str(facts.get("deal.amount") or 0)) * STAGE_PROBABILITY.get(facts.get("deal.stage"), Decimal(0))
        else:
            amount = Decimal(str(facts.get("invoice.outstanding") or 0))
        db.execute("INSERT INTO ems.leakage_findings (id, org_id, kind, entity_type, entity_id, fingerprint, amount_at_risk, currency, evidence) "
                   "VALUES (:id, :org, :k, :et, :eid, :fp, :amt, :cur, CAST(:ev AS jsonb)) ON CONFLICT (org_id, fingerprint) DO NOTHING",
                   id=uuid.uuid4(), org=org_id, k=action["kind"], et=kind, eid=entity_id, fp=f"rule:{rule['key']}:{entity_id}:{event_id}",
                   amt=amount.quantize(Decimal("0.01")), cur=facts.get("deal.currency") or facts.get("invoice.currency"),
                   ev=jsonb({"rule": rule["key"], "facts": facts}))


# ------------------------------------------------------------------------------------------------ runner
TRIGGER_FOR_EVENT = {"room.checked_in": "attendance.late", "task.overdue": "task.overdue", "leave.requested": "leave.requested",
                     "prospect.scored": "prospect.scored", "deal.stale": "deal.stale", "invoice.overdue": "invoice.overdue"}


def active_rules(db: Db, trigger: str) -> list[dict[str, Any]]:
    """The newest enabled version of each rule key for the trigger (saving a version disables the older ones)."""
    return db.all("SELECT DISTINCT ON (key) id, key, version, trigger, definition FROM ems.rules WHERE trigger = :t AND enabled "
                  "ORDER BY key, version DESC", t=trigger)


def run_for_event(db: Db, org_id: uuid.UUID, event_id: uuid.UUID, routing_key: str, payload: dict[str, Any]) -> int:
    """Evaluate every active rule for the event's trigger. Returns the number of runs recorded."""
    trigger = TRIGGER_FOR_EVENT.get(routing_key)
    if trigger is None:
        return 0
    rules = active_rules(db, trigger)
    if not rules:
        return 0
    ctx = context_for(db, trigger, payload)
    if ctx is None:
        return 0
    facts, people = ctx
    depth = int(payload.get("chain_depth", 0))
    recorded = 0
    for rule in rules:
        if db.scalar("SELECT 1 FROM ems.rule_runs WHERE rule_id = :r AND event_id = :e", r=rule["id"], e=event_id):
            continue                                                 # replayed event: already ran (DB-12)
        done: list[str] = []
        if depth >= MAX_CHAIN_DEPTH:
            outcome = "skipped_loop"
        else:
            matched, _ = engine.evaluate(rule["definition"]["when"], facts)
            outcome = "matched" if matched else "not_matched"
            if matched:
                try:
                    with db.savepoint():
                        for action in rule["definition"]["then"]:
                            execute(db, org_id, rule, event_id, action, facts, people, depth)
                            done.append(action["action"])
                except Exception:  # noqa: BLE001 - any action error is recorded on the run, the event itself succeeds
                    log.warning("rule action failed", exc_info=True, extra={"fields": {"rule": rule["key"], "event_id": str(event_id)}})
                    outcome, done = "action_failed", []              # the savepoint undid every action of this rule
        db.execute("INSERT INTO ems.rule_runs (id, org_id, rule_id, event_id, outcome, actions) VALUES (:id, :org, :r, :e, :o, CAST(:a AS jsonb)) "
                   "ON CONFLICT (rule_id, event_id) DO NOTHING",
                   id=uuid.uuid4(), org=org_id, r=rule["id"], e=event_id, o=outcome, a=jsonb(done))
        recorded += 1
    return recorded
