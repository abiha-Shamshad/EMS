"""Revenue leakage findings (API-065/066, spec Section 17). Amounts are estimates of money at risk, labelled as such."""
import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from app.platform.context import SessionCtx
from app.platform.db import Db, jsonb
from app.platform.errors import ApiError, invalid, not_found
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body
from app.platform.serialize import money

router = APIRouter(prefix="/api/v1/leakage")
KINDS = Literal["unbilled_time", "overdue_invoice", "stale_deal", "won_without_project", "won_without_invoice", "over_budget",
                "idle_paid_time", "retainer_underused"]


def _labels(db: Db, rows: list[dict[str, Any]]) -> dict[uuid.UUID, str]:
    """One human label per finding, from the record it is about (names looked up in one query per record type)."""
    ids: dict[str, list] = {}
    for r in rows:
        ids.setdefault(r["entity_type"], []).append(r["entity_id"])
    names: dict[Any, str] = {}
    lookups = {"deal": "SELECT id, title AS n FROM ems.deals WHERE id = ANY(:ids)",
               "project": "SELECT id, name AS n FROM ems.projects WHERE id = ANY(:ids)",
               "invoice": "SELECT id, number AS n FROM ems.invoices WHERE id = ANY(:ids)",
               "employee": "SELECT id, name AS n FROM ems.users WHERE id = ANY(:ids)",
               "task": "SELECT id, title AS n FROM ems.tasks WHERE id = ANY(:ids)"}
    for kind, sql in lookups.items():
        if ids.get(kind):
            names.update({r["id"]: r["n"] for r in db.all(sql, ids=ids[kind])})
    return {r["id"]: _label(r["kind"], names.get(r["entity_id"], "Deleted record"), r["evidence"] or {}) for r in rows}


def _label(kind: str, n: str, ev: dict[str, Any]) -> str:
    if kind == "overdue_invoice":
        return f"{ev.get('number', n)} overdue {ev.get('days_overdue', '?')} days"
    if kind == "stale_deal":
        return f"{n} - no activity {ev.get('days_without_activity', '?')} days"
    if kind == "unbilled_time":
        return f"{n} - {round(ev.get('minutes', 0) / 60, 1):g} h unbilled"
    if kind in ("won_without_project", "won_without_invoice"):
        return f"{n} - won {ev.get('days_since_won', '?')} days ago, no {kind.rsplit('_', 1)[1]}"
    if kind == "over_budget":
        return f"{n} - cost at {round(float(ev.get('ratio', 0)) * 100)}% of budget"
    if kind == "idle_paid_time":
        return f"{n} - {ev.get('idle_minutes', '?')} idle minutes (review with the employee)"
    return f"{kind.replace('_', ' ').capitalize()}: {n}"


# ------------------------------------------------------------------------------------------------ API-065
@router.get("/findings")
def findings(ctx: SessionCtx, status: Literal["open", "resolved", "dismissed"] = "open", kind: KINDS | None = None,
             cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    ctx.require("leakage.read", "Only the CEO, CFO and COO can see leakage findings.")
    db, base = ctx.db, ctx.org["base_currency"]
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = db.all(
        "SELECT id, kind, entity_type, entity_id, amount_at_risk, currency, evidence, status, detected_at, resolved_at FROM ems.leakage_findings "
        "WHERE status = :st AND (CAST(:k AS text) IS NULL OR kind = :k) "
        "AND (CAST(:a_amt AS numeric) IS NULL OR (coalesce(amount_at_risk, 0), id) < (CAST(:a_amt AS numeric), CAST(:a_id AS uuid))) "
        "ORDER BY coalesce(amount_at_risk, 0) DESC, id DESC LIMIT :lim",                  # largest money at risk first
        st=status, k=kind, a_amt=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [str(r["amount_at_risk"] or 0), str(r["id"])])
    labels = _labels(db, rows)
    totals = db.one("SELECT count(*) AS n, coalesce(sum(amount_at_risk) FILTER (WHERE currency = :c), 0) AS amount, "
                    "count(*) FILTER (WHERE currency IS NOT NULL AND currency <> :c) AS other FROM ems.leakage_findings WHERE status = 'open'",
                    c=base)
    data = {"totals": {"open": totals["n"], "amount_at_risk": money(totals["amount"]), "currency": base},
            "items": [{"id": r["id"], "kind": r["kind"], "label": labels[r["id"]], "amount_at_risk": money(r["amount_at_risk"]),
                       "currency": r["currency"], "evidence": r["evidence"], "status": r["status"], "detected_at": r["detected_at"]}
                      for r in rows],
            "next_cursor": next_cursor, "last_scan_at": db.scalar("SELECT leakage_scanned_at FROM ems.organizations"),
            "note": "Amounts are estimates of money at risk."}
    if totals["other"]:
        data["note"] += f" {totals['other']} open finding(s) in other currencies are not in the total."
    return ok(data)


# ------------------------------------------------------------------------------------------------ API-066
class ResolveIn(Body):
    resolution: Literal["resolved", "dismissed"]
    note: str | None = Field(default=None, max_length=500)


@router.post("/findings/{finding_id}/resolve")
def resolve(finding_id: uuid.UUID, body: ResolveIn, ctx: SessionCtx):
    ctx.require("leakage.resolve", "Only the CEO and CFO can resolve leakage findings.")
    if body.resolution == "dismissed" and not body.note:
        raise invalid("Say why the finding is dismissed.", {"note": "Required when dismissing."})
    db = ctx.db
    extra = {"resolution_note": body.note} if body.note else {}
    row = db.one("UPDATE ems.leakage_findings SET status = :st, resolved_by = :u, resolved_at = now(), evidence = evidence || CAST(:ev AS jsonb) "
                 "WHERE id = :f AND status = 'open' RETURNING id, status, resolved_at",            # first resolution wins
                 st=body.resolution, u=ctx.user_id, ev=jsonb(extra), f=finding_id)
    if row is None:
        if db.scalar("SELECT 1 FROM ems.leakage_findings WHERE id = :f", f=finding_id):
            raise ApiError("ALREADY_RESOLVED", "This finding was already resolved.")
        raise not_found("Finding")
    ctx.audit("leakage.resolved", "leakage_finding", finding_id, ["status"] + (["resolution_note"] if body.note else []))
    ctx.emit("leakage.resolved", {"finding_id": str(finding_id), "resolution": body.resolution})
    name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=ctx.user_id)
    return ok({"id": row["id"], "status": row["status"], "resolved_by": name, "resolved_at": row["resolved_at"]})
