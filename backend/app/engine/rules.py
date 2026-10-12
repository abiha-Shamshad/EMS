"""Deterministic rule engine (proposed path: backend/app/engine/rules.py). Standard library only.

A rule definition is JSON:
  {"trigger": "deal.stale",
   "when": {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 14},
                    {"any": [{"fact": "deal.stage", "op": "in", "value": ["proposal", "negotiation"]}]}]},
   "then": [{"action": "notify", "to": "owner", "template": "deal_stale"},
            {"action": "create_task", "assign": "owner", "title": "Follow up: {deal.title}", "due_in_hours": 24}]}
No code, expressions or URLs are accepted. Facts are looked up in a flat dict supplied by the caller.
"""
from typing import Any

OPS = {
    "eq": lambda a, b: a == b, "neq": lambda a, b: a != b,
    "gt": lambda a, b: a is not None and a > b, "gte": lambda a, b: a is not None and a >= b,
    "lt": lambda a, b: a is not None and a < b, "lte": lambda a, b: a is not None and a <= b,
    "in": lambda a, b: a in b, "not_in": lambda a, b: a not in b,
    "contains": lambda a, b: a is not None and b in a, "is_empty": lambda a, b: (a in (None, "", [], {})) == bool(b),
}
ACTIONS = {"notify", "create_task", "assign_owner", "set_stage_flag", "create_finding", "escalate"}
TRIGGER_FACTS = {
    "deal.stale": {"deal.days_since_activity", "deal.stage", "deal.amount", "deal.owner_role"},
    "task.overdue": {"task.hours_overdue", "task.status", "task.billable", "project.billing_type"},
    "attendance.late": {"employee.minutes_late", "employee.late_count_7d", "employee.role", "employee.department", "day.is_holiday"},
    "invoice.overdue": {"invoice.days_overdue", "invoice.outstanding", "client.status"},
    "leave.requested": {"leave.days", "leave.kind", "employee.leave_balance", "team.on_leave_count"},
    "prospect.scored": {"prospect.score", "prospect.has_public_email", "prospect.country"},
}
MAX_DEPTH, MAX_CONDITIONS, MAX_ACTIONS = 3, 20, 5


class RuleError(ValueError):
    pass


def validate(defn: dict) -> None:
    """Raise RuleError if the definition is not allowed. Call before saving a rule."""
    if set(defn) - {"trigger", "when", "then"}:
        raise RuleError("UNKNOWN_KEYS")
    trig = defn.get("trigger")
    if trig not in TRIGGER_FACTS:
        raise RuleError("UNKNOWN_TRIGGER")
    count = [0]

    def walk(node, depth):
        if depth > MAX_DEPTH:
            raise RuleError("TOO_DEEP")
        if "all" in node or "any" in node:
            key = "all" if "all" in node else "any"
            if set(node) != {key} or not isinstance(node[key], list) or not node[key]:
                raise RuleError("BAD_GROUP")
            for child in node[key]:
                walk(child, depth + 1)
            return
        if set(node) != {"fact", "op", "value"}:
            raise RuleError("BAD_CONDITION")
        if node["fact"] not in TRIGGER_FACTS[trig]:
            raise RuleError("FACT_NOT_ALLOWED:" + str(node["fact"]))
        if node["op"] not in OPS:
            raise RuleError("OP_NOT_ALLOWED:" + str(node["op"]))
        count[0] += 1
        if count[0] > MAX_CONDITIONS:
            raise RuleError("TOO_MANY_CONDITIONS")

    walk(defn.get("when") or {}, 1)
    actions = defn.get("then") or []
    if not actions or len(actions) > MAX_ACTIONS:
        raise RuleError("ACTION_COUNT")
    for a in actions:
        if a.get("action") not in ACTIONS:
            raise RuleError("ACTION_NOT_ALLOWED:" + str(a.get("action")))


def evaluate(node: dict, facts: dict[str, Any]) -> tuple[bool, list[dict]]:
    """Return (matched, trace). The trace lists every leaf condition and its result, for simulation and logs."""
    trace: list[dict] = []

    def ev(n):
        if "all" in n:
            return all([ev(c) for c in n["all"]])        # list, not generator: trace every condition
        if "any" in n:
            return any([ev(c) for c in n["any"]])
        actual = facts.get(n["fact"])
        try:
            ok = bool(OPS[n["op"]](actual, n["value"]))
        except TypeError:
            ok = False
        trace.append({"fact": n["fact"], "op": n["op"], "value": n["value"], "actual": actual, "result": ok})
        return ok

    return ev(node), trace


def render(template: str, facts: dict[str, Any]) -> str:
    """Replace {fact.name} placeholders with fact values; unknown placeholders stay visible."""
    out = template
    for k, v in facts.items():
        out = out.replace("{" + k + "}", str(v))
    return out


def run(defn: dict, facts: dict[str, Any]) -> dict:
    validate(defn)
    matched, trace = evaluate(defn["when"], facts)
    actions = []
    if matched:
        for a in defn["then"]:
            actions.append({k: (render(v, facts) if isinstance(v, str) else v) for k, v in a.items()})
    return {"matched": matched, "trace": trace, "actions": actions}
