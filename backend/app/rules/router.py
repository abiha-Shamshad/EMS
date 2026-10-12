"""Automation: rules and their run log (API-061..064, spec Section 15, TASK-013)."""
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from app.engine import rules as engine
from app.platform.context import Ctx, SessionCtx
from app.platform.db import jsonb
from app.platform.errors import ApiError, invalid, not_found
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body
from app.rules import service

router = APIRouter(prefix="/api/v1")
DENIED = "Only leadership can manage automations."
REASON_MESSAGES = {
    "UNKNOWN_KEYS": "A rule has only trigger, when and then.",
    "UNKNOWN_TRIGGER": "That trigger does not exist.",
    "TOO_DEEP": "Conditions can be nested at most 3 levels deep.",
    "BAD_GROUP": "Each 'all' or 'any' group needs a non-empty list of conditions.",
    "BAD_CONDITION": "Each condition needs exactly fact, op and value.",
    "TOO_MANY_CONDITIONS": "A rule can have at most 20 conditions.",
    "ACTION_COUNT": "A rule needs 1 to 5 actions.",
}


def _message(reason: str, trigger: str | None) -> str:
    code, _, detail = reason.partition(":")
    if code == "FACT_NOT_ALLOWED":
        return f"Fact '{detail}' is not available for trigger {trigger}."
    if code == "OP_NOT_ALLOWED":
        return f"Operator '{detail}' is not allowed."
    if code == "ACTION_NOT_ALLOWED":
        return f"Action '{detail}' is not allowed."
    if code == "RECIPIENT_NOT_ALLOWED":
        return f"'{detail}' cannot be resolved for trigger {trigger}."
    return REASON_MESSAGES.get(code, "The rule definition is not valid.")


def _require(ctx: Ctx, message: str = DENIED) -> None:
    ctx.require("rules.manage", message)


# ------------------------------------------------------------------------------------------------ API-061
@router.get("/rules")
def list_rules(ctx: SessionCtx):
    _require(ctx)
    rows = ctx.db.all(
        "SELECT r.id, r.key, r.version, r.trigger, r.enabled, "
        "count(x.id) AS runs, count(x.id) FILTER (WHERE x.outcome = 'matched') AS matched, "
        "count(x.id) FILTER (WHERE x.outcome = 'action_failed') AS failed "
        "FROM (SELECT DISTINCT ON (key) id, key, version, trigger, enabled FROM ems.rules ORDER BY key, version DESC) r "
        "LEFT JOIN ems.rule_runs x ON x.rule_id = r.id AND x.ran_at > now() - interval '7 days' "
        "GROUP BY r.id, r.key, r.version, r.trigger, r.enabled ORDER BY r.key")
    return ok({"items": [{"id": r["id"], "key": r["key"], "version": r["version"], "trigger": r["trigger"], "enabled": r["enabled"],
                          "runs_7d": r["runs"], "matched_7d": r["matched"], "failed_7d": r["failed"]} for r in rows],
               "external_api_calls_7d": 0})                                     # the engine makes no external calls (Section 15)


# ------------------------------------------------------------------------------------------------ API-062
class RuleIn(Body):
    key: str = Field(pattern=r"^[a-z0-9_]{3,60}$")
    definition: dict[str, Any]


@router.post("/rules", status_code=201)
def create_rule(body: RuleIn, ctx: SessionCtx, idem: IdemKey):
    _require(ctx)
    try:
        service.validate(body.definition)
    except engine.RuleError as exc:
        reason = str(exc)
        raise ApiError("RULE_INVALID", _message(reason, body.definition.get("trigger")), {"reason": reason}) from exc
    if len(jsonb(body.definition)) > 20_000:
        raise invalid("The rule definition is too large.", {"definition": "At most 20 000 characters."})

    def handler():
        db = ctx.db
        db.execute("SELECT pg_advisory_xact_lock(hashtext(CAST(:org AS text) || :name))", org=str(ctx.org_id), name=f":rule:{body.key}")
        version = db.scalar("SELECT coalesce(max(version), 0) + 1 FROM ems.rules WHERE key = :k", k=body.key)
        rule_id = uuid.uuid4()
        db.execute("UPDATE ems.rules SET enabled = false WHERE key = :k AND enabled", k=body.key)    # only the newest version runs
        db.execute("INSERT INTO ems.rules (id, org_id, key, version, trigger, definition, created_by) "
                   "VALUES (:id, :org, :k, :v, :t, CAST(:d AS jsonb), :u)",
                   id=rule_id, org=ctx.org_id, k=body.key, v=version, t=body.definition["trigger"], d=jsonb(body.definition), u=ctx.user_id)
        ctx.audit("rule.created", "rule", rule_id, ["definition"])
        ctx.emit("rule.created", {"rule_id": str(rule_id), "key": body.key, "version": version})
        return ok({"id": rule_id, "key": body.key, "version": version, "enabled": True}, "Rule saved.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-063
class SimulateIn(Body):
    facts: dict[str, Any] = Field(max_length=50)


@router.post("/rules/{rule_id}/simulate")
def simulate(rule_id: uuid.UUID, body: SimulateIn, ctx: SessionCtx):
    _require(ctx)
    rule = ctx.db.one("SELECT definition FROM ems.rules WHERE id = :r", r=rule_id)
    if rule is None:
        raise not_found("Rule")
    return ok(engine.run(rule["definition"], body.facts))                     # pure: no side effects


# ------------------------------------------------------------------------------------------------ API-064
@router.get("/rule-runs")
def rule_runs(ctx: SessionCtx, rule_id: uuid.UUID | None = None,
              outcome: Literal["matched", "not_matched", "action_failed", "skipped_loop"] | None = None,
              cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    _require(ctx, "Only leadership can view automation logs.")
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT x.id, r.key, r.trigger, x.outcome, x.actions, x.ran_at FROM ems.rule_runs x JOIN ems.rules r ON r.id = x.rule_id "
        "WHERE (CAST(:rid AS uuid) IS NULL OR x.rule_id = :rid) AND (CAST(:o AS text) IS NULL OR x.outcome = :o) "
        "AND (CAST(:a_t AS timestamptz) IS NULL OR (x.ran_at, x.id) < (CAST(:a_t AS timestamptz), CAST(:a_id AS uuid))) "
        "ORDER BY x.ran_at DESC, x.id DESC LIMIT :lim",
        rid=rule_id, o=outcome, a_t=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["ran_at"].isoformat(), str(r["id"])])
    return ok({"items": [{"id": r["id"], "rule": r["key"], "event": r["trigger"], "outcome": r["outcome"], "actions": r["actions"],
                          "ran_at": r["ran_at"]} for r in rows], "next_cursor": next_cursor})
