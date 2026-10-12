"""CRM and the client lifecycle (API-045..052, spec Section 13)."""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy.exc import IntegrityError

from app.crm.suppression import is_suppressed
from app.engine.leakage import STAGE_PROBABILITY
from app.graph import service as graph
from app.platform.context import Ctx, SessionCtx
from app.platform.db import like_pattern
from app.platform.errors import ApiError, denied, invalid, not_found, version_conflict
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body, Currency, Domain, Email, ExpectedVersion, Money
from app.platform.serialize import money
from app.platform.timeutil import utcnow
from app.projects import service as projects

router = APIRouter(prefix="/api/v1")
OPEN_STAGES = ("new", "qualified", "proposal", "negotiation")
STALE_DAYS = 14
FUTURE_SKEW = dt.timedelta(minutes=5)


def _require_crm_read(ctx: Ctx) -> None:
    """crm.manage, or the CFO's read access to contacts and pipeline (Section 7.2)."""
    if not (ctx.can("crm.manage") or ctx.role == "cfo"):
        raise denied("Only sales leadership and managers can open the CRM.")


def find_or_create_company(ctx: Ctx, name: str, domain: str | None) -> uuid.UUID:
    db = ctx.db
    existing = (db.scalar("SELECT id FROM ems.companies WHERE domain = :d", d=domain) if domain
                else db.scalar("SELECT id FROM ems.companies WHERE lower(name) = lower(:n) AND domain IS NULL LIMIT 1", n=name))
    if existing:
        return existing
    company_id = uuid.uuid4()
    try:
        with db.savepoint():
            db.execute("INSERT INTO ems.companies (id, org_id, name, domain) VALUES (:id, :org, :n, :d)",
                       id=company_id, org=ctx.org_id, n=name, d=domain)
    except IntegrityError:                               # concurrent insert of the same domain
        return db.scalar("SELECT id FROM ems.companies WHERE domain = :d", d=domain)
    return company_id


# ------------------------------------------------------------------------------------------------ API-045
class CompanyIn(Body):
    name: str = Field(min_length=1, max_length=200)
    domain: Domain | None = None


class ContactIn(Body):
    name: str = Field(min_length=1, max_length=200)
    email: Email | None = None
    phone: str | None = Field(default=None, max_length=40)
    company: CompanyIn | None = None
    source: Literal["manual", "import", "lead_hunter", "referral", "website"] = "manual"
    owner_id: uuid.UUID | None = None


@router.post("/contacts", status_code=201)
def create_contact(body: ContactIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("crm.manage", "Only sales leadership and managers can add contacts.")

    def handler():
        db = ctx.db
        if is_suppressed(db, email=body.email, domain=body.company.domain if body.company else None):
            raise ApiError("SUPPRESSED_CONTACT", "This email asked not to be contacted. It cannot be added as a lead.")
        if body.email:
            dup = db.one("SELECT id, lifecycle_stage FROM ems.contacts WHERE email = :e", e=body.email)
            if dup:
                return ok({"id": dup["id"], "lifecycle_stage": dup["lifecycle_stage"], "already_exists": True})
        owner = body.owner_id or ctx.user_id
        projects.require_active_member(db, owner, "owner")
        company_id = find_or_create_company(ctx, body.company.name, body.company.domain) if body.company else None
        contact_id = uuid.uuid4()
        try:
            with db.savepoint():
                db.execute("INSERT INTO ems.contacts (id, org_id, company_id, name, email, phone, owner_id, source) "
                           "VALUES (:id, :org, :c, :n, :e, :p, :o, :s)",
                           id=contact_id, org=ctx.org_id, c=company_id, n=body.name, e=body.email, p=body.phone, o=owner, s=body.source)
        except IntegrityError:                           # same email added concurrently
            dup = db.one("SELECT id, lifecycle_stage FROM ems.contacts WHERE email = :e", e=body.email)
            return ok({"id": dup["id"], "lifecycle_stage": dup["lifecycle_stage"], "already_exists": True})
        ctx.audit("contact.created", "contact", contact_id)
        ctx.emit("contact.created", {"contact_id": str(contact_id), "company_id": str(company_id) if company_id else None})
        owner_name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=owner)
        return ok({"id": contact_id, "lifecycle_stage": "lead", "company_id": company_id, "owner": owner_name, "version": 1},
                  "Lead added.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-046
class ContactSearchIn(Body):
    query: str | None = Field(default=None, max_length=200)
    lifecycle_stage: list[Literal["lead", "qualified", "opportunity", "customer", "churned", "disqualified"]] | None = None
    owner_id: uuid.UUID | None = None
    source: list[Literal["manual", "import", "lead_hunter", "referral", "website"]] | None = None
    limit: int | None = None
    cursor: str | None = None


@router.post("/contacts/search")
def search_contacts(body: ContactSearchIn, ctx: SessionCtx):
    _require_crm_read(ctx)
    if body.query is not None and len(body.query) < 2:
        raise ApiError("VALIDATION_FAILED", "Search text must be at least 2 characters.")
    limit, after = clamp_limit(body.limit), decode_cursor(body.cursor, 2)
    pattern = like_pattern(body.query.lower()) if body.query else None
    rows = ctx.db.all(
        "SELECT c.id, c.name, co.name AS company, c.lifecycle_stage, ou.name AS owner, "
        "(SELECT max(a.occurred_at) FROM ems.activities a WHERE (a.entity_type = 'contact' AND a.entity_id = c.id) "
        "  OR (a.entity_type = 'deal' AND a.entity_id IN (SELECT d.id FROM ems.deals d WHERE d.contact_id = c.id))) AS last_activity_at "
        "FROM ems.contacts c LEFT JOIN ems.companies co ON co.id = c.company_id LEFT JOIN ems.users ou ON ou.id = c.owner_id "
        "WHERE (CAST(:pat AS text) IS NULL OR (lower(c.name) || ' ' || coalesce(c.email, '')) LIKE :pat OR lower(co.name) LIKE :pat) "
        "AND (CAST(:stages AS text[]) IS NULL OR c.lifecycle_stage = ANY(CAST(:stages AS text[]))) "
        "AND (CAST(:sources AS text[]) IS NULL OR c.source = ANY(CAST(:sources AS text[]))) "
        "AND (CAST(:owner AS uuid) IS NULL OR c.owner_id = :owner) "
        "AND (CAST(:a_name AS text) IS NULL OR (c.name, c.id) > (:a_name, CAST(:a_id AS uuid))) "
        "ORDER BY c.name, c.id LIMIT :lim",
        pat=pattern, stages=body.lifecycle_stage, sources=body.source, owner=body.owner_id,
        a_name=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["name"], str(r["id"])])
    return ok({"items": rows, "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-047
@router.get("/contacts/{contact_id}")
def contact_details(contact_id: uuid.UUID, ctx: SessionCtx):
    _require_crm_read(ctx)
    db = ctx.db
    c = db.one("SELECT c.id, c.name, c.email, c.phone, c.lifecycle_stage, c.source, c.version, c.company_id, co.name AS company_name, "
               "ou.name AS owner FROM ems.contacts c LEFT JOIN ems.companies co ON co.id = c.company_id "
               "LEFT JOIN ems.users ou ON ou.id = c.owner_id WHERE c.id = :c", c=contact_id)
    if c is None:
        raise not_found("Contact")
    deals = db.all("SELECT id, title, stage, amount, currency, version FROM ems.deals WHERE contact_id = :c ORDER BY created_at DESC",
                   c=contact_id)
    activities = db.all(
        "SELECT a.entity_type, a.kind, a.note, a.occurred_at, u.name AS actor FROM ems.activities a LEFT JOIN ems.users u ON u.id = a.actor_id "
        "WHERE (a.entity_type = 'contact' AND a.entity_id = :c) OR (a.entity_type = 'deal' AND a.entity_id = ANY(:deals)) "
        "ORDER BY a.occurred_at DESC LIMIT 50", c=contact_id, deals=[d["id"] for d in deals])
    node = graph.node_for(db, "contact", contact_id)
    related = graph.neighbors(ctx, node["id"], 3)[:25] if node else []
    return ok({"id": c["id"], "name": c["name"], "email": c["email"], "phone": c["phone"],
               "company": {"id": c["company_id"], "name": c["company_name"]} if c["company_id"] else None,
               "lifecycle_stage": c["lifecycle_stage"], "source": c["source"], "owner": c["owner"], "version": c["version"],
               "deals": [{**d, "amount": money(d["amount"])} for d in deals], "activities": activities,
               "related": [{"kind": r["kind"], "label": r["label"], "via": r["via"]} for r in related]})


# ------------------------------------------------------------------------------------------------ API-048
class DealIn(Body):
    contact_id: uuid.UUID
    title: str = Field(min_length=1, max_length=200)
    amount: Money
    currency: Currency
    expected_close: dt.date | None = None
    owner_id: uuid.UUID | None = None


@router.post("/deals", status_code=201)
def create_deal(body: DealIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("crm.manage", "Only sales leadership and managers can create deals.")

    def handler():
        db = ctx.db
        contact = db.one("SELECT id, company_id, lifecycle_stage FROM ems.contacts WHERE id = :c", c=body.contact_id)
        if contact is None:
            raise invalid("That contact does not exist.", {"contact_id": "Unknown contact."})
        owner = body.owner_id or ctx.user_id
        projects.require_active_member(db, owner, "owner")
        deal_id = uuid.uuid4()
        db.execute("INSERT INTO ems.deals (id, org_id, contact_id, company_id, title, amount, currency, owner_id, expected_close) "
                   "VALUES (:id, :org, :c, :co, :t, :a, :cur, :o, :ec)",
                   id=deal_id, org=ctx.org_id, c=body.contact_id, co=contact["company_id"], t=body.title, a=body.amount,
                   cur=body.currency, o=owner, ec=body.expected_close)
        if contact["lifecycle_stage"] in ("lead", "qualified"):
            db.execute("UPDATE ems.contacts SET lifecycle_stage = 'opportunity', version = version + 1 WHERE id = :c", c=body.contact_id)
        ctx.audit("deal.created", "deal", deal_id)
        ctx.emit("deal.created", {"deal_id": str(deal_id), "contact_id": str(body.contact_id)})
        return ok({"id": deal_id, "stage": "new", "version": 1}, "Deal created.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-049
@router.get("/deals/pipeline")
def pipeline(ctx: SessionCtx, owner_id: uuid.UUID | None = None, currency: Annotated[str | None, Query(pattern=r"^[A-Z]{3}$")] = None):
    _require_crm_read(ctx)
    db, cal = ctx.db, ctx.calendar
    currencies = [r["currency"] for r in db.all(
        "SELECT DISTINCT currency FROM ems.deals WHERE stage = ANY(:open) AND (CAST(:o AS uuid) IS NULL OR owner_id = :o) ORDER BY currency",
        open=list(OPEN_STAGES), o=owner_id)]
    if currency is None:
        if len(currencies) > 1:
            raise ApiError("CURRENCY_REQUIRED", f"Choose a currency; deals exist in {' and '.join(currencies)}.", {"currencies": currencies})
        currency = currencies[0] if currencies else ctx.org["base_currency"]
    rows = {r["stage"]: r for r in db.all(
        "SELECT stage, count(*) AS count, coalesce(sum(amount), 0) AS amount FROM ems.deals "
        "WHERE stage = ANY(:open) AND currency = :cur AND (CAST(:o AS uuid) IS NULL OR owner_id = :o) GROUP BY stage",
        open=list(OPEN_STAGES), cur=currency, o=owner_id)}
    stages, weighted = [], Decimal(0)
    for s in OPEN_STAGES:
        r = rows.get(s, {"count": 0, "amount": Decimal(0)})
        stages.append({"stage": s, "count": r["count"], "amount": money(r["amount"])})
        weighted += Decimal(r["amount"]) * STAGE_PROBABILITY[s]
    today = cal.local_date()
    month_start = cal.day_bounds(today.replace(day=1))[0]
    won = db.one("SELECT count(*) AS count, coalesce(sum(amount), 0) AS amount FROM ems.deals WHERE stage = 'won' AND currency = :cur "
                 "AND won_at >= :ms AND (CAST(:o AS uuid) IS NULL OR owner_id = :o)", cur=currency, ms=month_start, o=owner_id)
    stale = db.scalar("SELECT count(*) FROM ems.deals WHERE stage = ANY(:open) AND currency = :cur AND last_activity_at < :t "
                      "AND (CAST(:o AS uuid) IS NULL OR owner_id = :o)",
                      open=list(OPEN_STAGES), cur=currency, t=utcnow() - dt.timedelta(days=STALE_DAYS), o=owner_id)
    return ok({"currency": currency, "stages": stages, "weighted_open": money(weighted),
               "won_this_month": {"count": won["count"], "amount": money(won["amount"])}, "stale_count": stale})


# ------------------------------------------------------------------------------------------------ deals board (web)
@router.get("/deals")
def list_deals(ctx: SessionCtx, stage: Literal["new", "qualified", "proposal", "negotiation", "won", "lost"] | None = None,
               owner_id: uuid.UUID | None = None, cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    """Deal cards for the pipeline board. Read-only companion to API-049 (the contract has totals, not cards)."""
    _require_crm_read(ctx)
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT d.id, d.title, d.stage, d.amount, d.currency, d.expected_close, d.last_activity_at, d.version, d.owner_id, "
        "u.name AS owner, c.id AS contact_id, c.name AS contact, co.name AS company FROM ems.deals d "
        "JOIN ems.users u ON u.id = d.owner_id JOIN ems.contacts c ON c.id = d.contact_id LEFT JOIN ems.companies co ON co.id = c.company_id "
        "WHERE (CAST(:st AS text) IS NULL OR d.stage = :st) AND (CAST(:o AS uuid) IS NULL OR d.owner_id = :o) "
        "AND (CAST(:a_t AS timestamptz) IS NULL OR (d.last_activity_at, d.id) < (CAST(:a_t AS timestamptz), CAST(:a_id AS uuid))) "
        "ORDER BY d.last_activity_at DESC, d.id DESC LIMIT :lim",
        st=stage, o=owner_id, a_t=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["last_activity_at"].isoformat(), str(r["id"])])
    stale_before = utcnow() - dt.timedelta(days=STALE_DAYS)
    return ok({"items": [{"id": r["id"], "title": r["title"], "stage": r["stage"], "amount": money(r["amount"]), "currency": r["currency"],
                          "expected_close": r["expected_close"], "last_activity_at": r["last_activity_at"], "version": r["version"],
                          "owner": {"id": r["owner_id"], "name": r["owner"]}, "contact": {"id": r["contact_id"], "name": r["contact"]},
                          "company": r["company"], "stale": r["stage"] in OPEN_STAGES and r["last_activity_at"] < stale_before}
                         for r in rows], "next_cursor": next_cursor})


@router.get("/clients")
def list_clients(ctx: SessionCtx, status: Literal["onboarding", "active", "at_risk", "churned"] | None = None):
    """Clients for the invoice and project forms. Read-only (CRM or finance access)."""
    if not (ctx.can("crm.manage") or ctx.can("finance.manage")):
        raise denied("Only sales, finance and leadership can list clients.")
    rows = ctx.db.all("SELECT c.id, co.name, c.status, c.since, c.renewal_date, d.title AS origin_deal FROM ems.clients c "
                      "JOIN ems.companies co ON co.id = c.company_id JOIN ems.deals d ON d.id = c.origin_deal_id "
                      "WHERE CAST(:st AS text) IS NULL OR c.status = :st ORDER BY co.name", st=status)
    return ok({"items": rows})


def _activity(ctx: Ctx, entity_type: str, entity_id: uuid.UUID, kind: str, note: str | None, at: dt.datetime) -> uuid.UUID:
    activity_id = uuid.uuid4()
    ctx.db.execute("INSERT INTO ems.activities (id, org_id, entity_type, entity_id, kind, note, actor_id, occurred_at) "
                   "VALUES (:id, :org, :et, :eid, :k, :n, :a, :t)",
                   id=activity_id, org=ctx.org_id, et=entity_type, eid=entity_id, k=kind, n=note, a=ctx.user_id, t=at)
    return activity_id


# ------------------------------------------------------------------------------------------------ API-050
class StageIn(Body):
    expected_version: ExpectedVersion
    to_stage: Literal["new", "qualified", "proposal", "negotiation", "won", "lost"]
    lost_reason: str | None = Field(default=None, min_length=1, max_length=500)


@router.post("/deals/{deal_id}/stage")
def move_deal(deal_id: uuid.UUID, body: StageIn, ctx: SessionCtx):
    ctx.require("crm.manage", "Only sales leadership and managers can move deals.")
    db = ctx.db
    deal = db.one("SELECT id, stage, version FROM ems.deals WHERE id = :d FOR UPDATE", d=deal_id)
    if deal is None:
        raise not_found("Deal")
    if body.to_stage == "won":
        raise ApiError("INVALID_TRANSITION", "Use 'Mark as won' to win a deal.", {"to": "won", "use": "/api/v1/deals/{dealId}/win"})
    if deal["stage"] not in OPEN_STAGES:
        raise ApiError("INVALID_TRANSITION", f"This deal is already {deal['stage']}.", {"from": deal["stage"], "allowed": []})
    if body.to_stage == "lost" and not body.lost_reason:
        raise ApiError("LOST_REASON_REQUIRED", "Say why the deal was lost.")
    if deal["version"] != body.expected_version:
        raise version_conflict(deal["version"], "This deal was changed by someone else.")
    now = utcnow()
    row = db.one("UPDATE ems.deals SET stage = :s, lost_reason = CASE WHEN :s = 'lost' THEN CAST(:r AS text) ELSE lost_reason END, "
                 "last_activity_at = :t, version = version + 1 WHERE id = :d RETURNING id, stage, version",
                 s=body.to_stage, r=body.lost_reason, t=now, d=deal_id)
    _activity(ctx, "deal", deal_id, "stage_change", f"{deal['stage']} -> {body.to_stage}", now)
    ctx.audit("deal.stage_changed", "deal", deal_id, ["stage"])
    ctx.emit("deal.stage_changed", {"deal_id": str(deal_id), "from_stage": deal["stage"], "to_stage": body.to_stage})
    return ok(row)


# ------------------------------------------------------------------------------------------------ API-051
class WinProjectIn(Body):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    billing_type: Literal["fixed", "hourly", "retainer"] = "fixed"
    budget_amount: Money | None = None
    hourly_rate: Money | None = None
    owner_id: uuid.UUID | None = None
    template: Literal["website_standard", "mobile_app_standard", "blank"] = "blank"


class WinIn(Body):
    expected_version: ExpectedVersion
    project: WinProjectIn | None = None
    renewal_date: dt.date | None = None


@router.post("/deals/{deal_id}/win")
def win_deal(deal_id: uuid.UUID, body: WinIn, ctx: SessionCtx, idem: IdemKey):
    """One transaction: deal won, client created, kickoff project from a template, contact becomes customer (DB-09)."""
    ctx.require("crm.manage", "Only sales leadership and managers can win deals.")
    spec = body.project or WinProjectIn()
    if spec.billing_type == "hourly" and spec.hourly_rate is None:
        raise invalid("Hourly projects need an hourly rate.", {"project.hourly_rate": "Required for hourly billing."})

    def handler():
        db = ctx.db
        deal = db.one("SELECT d.id, d.title, d.stage, d.version, d.amount, d.currency, d.owner_id, d.contact_id, "
                      "coalesce(d.company_id, c.company_id) AS company_id FROM ems.deals d JOIN ems.contacts c ON c.id = d.contact_id "
                      "WHERE d.id = :d FOR UPDATE OF d", d=deal_id)
        if deal is None:
            raise not_found("Deal")
        if deal["stage"] == "won":
            client_id = db.scalar("SELECT id FROM ems.clients WHERE origin_deal_id = :d", d=deal_id)
            raise ApiError("ALREADY_WON", "This deal is already won.", {"client_id": client_id})
        if deal["stage"] == "lost":
            raise ApiError("INVALID_TRANSITION", "A lost deal cannot be won.", {"from": "lost", "allowed": []})
        if deal["version"] != body.expected_version:
            raise version_conflict(deal["version"], "This deal was changed by someone else.")
        if deal["company_id"] is None:
            raise ApiError("COMPANY_REQUIRED", "Add the contact's company before winning the deal.")
        owner = spec.owner_id or deal["owner_id"]
        projects.require_active_member(db, owner, "project owner")

        now = utcnow()
        won = db.one("UPDATE ems.deals SET stage = 'won', won_at = :t, company_id = :co, last_activity_at = :t, version = version + 1 "
                     "WHERE id = :d RETURNING won_at", t=now, co=deal["company_id"], d=deal_id)
        client_id = uuid.uuid4()
        db.execute("INSERT INTO ems.clients (id, org_id, company_id, origin_deal_id, since, renewal_date) "
                   "VALUES (:id, :org, :co, :d, :since, :renew)",
                   id=client_id, org=ctx.org_id, co=deal["company_id"], d=deal_id, since=ctx.calendar.local_date(now), renew=body.renewal_date)
        budget = spec.budget_amount if spec.budget_amount is not None else (deal["amount"] if spec.billing_type == "fixed" else None)
        project_id = projects.insert_project(ctx, name=spec.name or deal["title"], client_id=client_id, billing_type=spec.billing_type,
                                             budget_amount=budget, hourly_rate=spec.hourly_rate, currency=deal["currency"], owner_id=owner)
        tasks_created = projects.apply_template(ctx, project_id, spec.template, billable=True)
        db.execute("UPDATE ems.contacts SET lifecycle_stage = 'customer', version = version + 1 WHERE id = :c", c=deal["contact_id"])
        _activity(ctx, "deal", deal_id, "stage_change", f"{deal['stage']} -> won", now)
        ctx.audit("deal.won", "deal", deal_id, ["stage", "won_at"])
        ctx.audit("client.created", "client", client_id)
        ctx.audit("project.created", "project", project_id)
        ctx.emit("deal.won", {"deal_id": str(deal_id), "client_id": str(client_id), "project_id": str(project_id),
                              "contact_id": str(deal["contact_id"])})
        return ok({"deal": {"id": deal_id, "stage": "won", "won_at": won["won_at"]}, "client": {"id": client_id, "status": "onboarding"},
                   "project": {"id": project_id, "status": "planned", "tasks_created": tasks_created}},
                  "Deal won. Client and project created.")

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-052
class ActivityIn(Body):
    entity_type: Literal["contact", "deal", "client", "project", "task", "employee"]
    entity_id: uuid.UUID
    kind: Literal["note", "call", "email", "meeting"]
    note: str | None = Field(default=None, max_length=2000)
    occurred_at: dt.datetime


ENTITY_TABLE = {"contact": "contacts", "deal": "deals", "client": "clients", "project": "projects", "task": "tasks"}


@router.post("/activities", status_code=201)
def log_activity(body: ActivityIn, ctx: SessionCtx, idem: IdemKey):
    if body.occurred_at.tzinfo is None:
        raise invalid("Send occurred_at in UTC with a Z suffix.", {"occurred_at": "Timezone required."})
    if body.occurred_at > utcnow() + FUTURE_SKEW:
        raise ApiError("VALIDATION_FAILED", "Activity time cannot be in the future.")

    def handler():
        db = ctx.db
        if body.entity_type == "employee":
            if not db.scalar("SELECT 1 FROM ems.memberships WHERE user_id = :u", u=body.entity_id):
                raise not_found("Employee")
            if not ctx.covers("hr.manage", body.entity_id):
                raise denied("Only HR and managers can add notes about employees.")
        else:
            table = ENTITY_TABLE[body.entity_type]
            if not db.scalar(f"SELECT 1 FROM ems.{table} WHERE id = :id", id=body.entity_id):  # noqa: S608 - table from fixed map
                raise not_found(body.entity_type.capitalize())
            if body.entity_type in ("project", "task") and not ctx.can("crm.manage"):
                project_id = body.entity_id if body.entity_type == "project" else db.scalar(
                    "SELECT project_id FROM ems.tasks WHERE id = :t", t=body.entity_id)
                projects.project_for(ctx, project_id)
            elif body.entity_type in ("contact", "deal", "client"):
                ctx.require("crm.manage", "Only sales leadership and managers can log CRM activities.")
        activity_id = _activity(ctx, body.entity_type, body.entity_id, body.kind, body.note, body.occurred_at)
        if body.entity_type == "deal":                   # resets the stale-deal timer (Section 13)
            db.execute("UPDATE ems.deals SET last_activity_at = greatest(last_activity_at, :t) WHERE id = :d",
                       t=body.occurred_at, d=body.entity_id)
        ctx.audit("activity.created", "activity", activity_id)
        ctx.emit("activity.created", {"activity_id": str(activity_id), "entity_type": body.entity_type, "entity_id": str(body.entity_id)})
        return ok({"id": activity_id, "entity_type": body.entity_type, "entity_id": body.entity_id}, status=201)

    return run_once(ctx, idem, handler)
