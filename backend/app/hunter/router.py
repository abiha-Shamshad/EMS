"""Lead Hunter (API-055..060, spec Section 14, TASK-012). The API queues hunts and works with their results; the crawl
itself runs in the worker (worker/jobs.py -> app/hunter/crawler.py). Outreach is a draft the user copies to their own
mail client: nothing is sent (INT-003 / OD-05)."""
import math
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field, field_validator
from sqlalchemy.exc import IntegrityError

from app.crm import suppression
from app.hunter.crawler import PAGES, REQUEST_GAP_SECONDS, TECH_LABELS, blocked
from app.platform.context import Ctx, SessionCtx
from app.platform.db import jsonb
from app.platform.errors import ApiError, denied, invalid, not_found
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body, is_valid_domain, normalize_domain, validate_email

router = APIRouter(prefix="/api/v1")
MAX_SEEDS = 200
STATS_KEYS = ("domains", "fetched_pages", "robots_disallowed", "unreachable", "prospects", "already_in_crm")


def _hunt(ctx: Ctx, hunt_id: uuid.UUID) -> dict:
    ctx.require("hunter.use", "Only leadership and managers can use the Lead Hunter.")
    h = ctx.db.one("SELECT id, name, status, stats, created_by FROM ems.hunts WHERE id = :h", h=hunt_id)
    if h is None:
        raise not_found("Hunt")
    return h


def _prospect(ctx: Ctx, prospect_id: uuid.UUID, lock: bool = False) -> dict:
    p = ctx.db.one("SELECT id, hunt_id, domain, company_name, public_emails, signals, score, status, contact_id "  # noqa: S608 - constant SQL
                   "FROM ems.prospects WHERE id = :p" + (" FOR UPDATE" if lock else ""), p=prospect_id)
    if p is None:
        raise not_found("Prospect")
    return p


def _suppressed(ctx: Ctx, p: dict) -> bool:
    return p["status"] == "suppressed" or suppression.is_suppressed(ctx.db, domain=p["domain"]) or any(
        suppression.is_suppressed(ctx.db, email=e) for e in p["public_emails"])


# ------------------------------------------------------------------------------------------------ API-055
class Seeds(Body):
    domains: list[str] = Field(min_length=1)

    @field_validator("domains")
    @classmethod
    def _domains(cls, v: list[str]) -> list[str]:
        if len(v) > MAX_SEEDS:
            raise ValueError(f"At most {MAX_SEEDS} domains per hunt.")
        out = []
        for raw in v:
            d = normalize_domain(raw)
            if not is_valid_domain(d):
                raise ValueError(f"'{raw}' is not a valid domain.")
            out.append(d)
        return list(dict.fromkeys(out))


class Icp(Body):
    industry_keywords: list[Annotated[str, Field(min_length=2, max_length=60)]] = Field(default_factory=list, max_length=20)
    countries: list[Annotated[str, Field(pattern=r"^[A-Z]{2}$")]] = Field(default_factory=list, max_length=50)
    tech: list[Annotated[str, Field(min_length=2, max_length=40)]] = Field(default_factory=list, max_length=20)
    min_team_size: int | None = Field(default=None, ge=1, le=100000)


class HuntIn(Body):
    name: str = Field(min_length=1, max_length=120)
    seeds: Seeds
    icp: Icp
    max_pages_per_domain: int = Field(default=len(PAGES), ge=1, le=len(PAGES))


@router.post("/hunts", status_code=202)
def start_hunt(body: HuntIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("hunter.use", "Only leadership and managers can use the Lead Hunter.")
    for d in body.seeds.domains:
        if blocked(d):
            raise ApiError("SOURCE_NOT_ALLOWED", f"{d} cannot be crawled. Use company websites you are allowed to visit.", {"domain": d})

    def handler():
        hunt_id = uuid.uuid4()
        seeds = {"domains": body.seeds.domains, "max_pages_per_domain": body.max_pages_per_domain}
        ctx.db.execute("INSERT INTO ems.hunts (id, org_id, name, seeds, icp, stats, created_by) "
                       "VALUES (:id, :org, :n, CAST(:s AS jsonb), CAST(:i AS jsonb), CAST(:st AS jsonb), :u)",
                       id=hunt_id, org=ctx.org_id, n=body.name, s=jsonb(seeds), i=jsonb(body.icp.model_dump()),
                       st=jsonb({"domains": len(body.seeds.domains)}), u=ctx.user_id)
        ctx.audit("hunt.created", "hunt", hunt_id)
        ctx.emit("hunt.created", {"hunt_id": str(hunt_id), "domains": len(body.seeds.domains)})
        # Domains are crawled round-robin, one request per domain every 5 s: about (pages + robots.txt) x 5 s plus fetch time.
        requests = body.max_pages_per_domain + 1
        seconds = requests * REQUEST_GAP_SECONDS + len(body.seeds.domains) * requests * 2
        return ok({"hunt_id": hunt_id, "status": "queued", "domains": len(body.seeds.domains),
                   "estimated_minutes": max(1, math.ceil(seconds / 60))}, "Hunt started.", status=202)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-056
@router.get("/hunts/{hunt_id}")
def hunt_status(hunt_id: uuid.UUID, ctx: SessionCtx):
    h = _hunt(ctx, hunt_id)
    stats = {k: int((h["stats"] or {}).get(k, 0)) for k in STATS_KEYS}
    if "suppressed" in (h["stats"] or {}):
        stats["suppressed"] = int(h["stats"]["suppressed"])
    return ok({"hunt_id": h["id"], "name": h["name"], "status": h["status"], "stats": stats})


# ------------------------------------------------------------------------------------------------ API-057
@router.get("/hunts/{hunt_id}/prospects")
def hunt_prospects(hunt_id: uuid.UUID, ctx: SessionCtx, min_score: Annotated[int, Query(ge=0, le=100)] = 0,
                   cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    _hunt(ctx, hunt_id)
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT id, domain, company_name, score, score_reasons, public_emails, source_url, status FROM ems.prospects "
        "WHERE hunt_id = :h AND score >= :min "
        "AND (CAST(:a_s AS integer) IS NULL OR (score, id) < (CAST(:a_s AS integer), CAST(:a_id AS uuid))) "
        "ORDER BY score DESC, id DESC LIMIT :lim",
        h=hunt_id, min=min_score, a_s=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["score"], str(r["id"])])
    return ok({"items": [{**r, "public_emails": list(r["public_emails"])} for r in rows], "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-058
class PromoteIn(Body):
    owner_id: uuid.UUID | None = None


@router.post("/prospects/{prospect_id}/promote", status_code=201)
def promote(prospect_id: uuid.UUID, body: PromoteIn, ctx: SessionCtx):
    ctx.require("hunter.use", "Only leadership and managers can use the Lead Hunter.")
    ctx.require("crm.manage", "You need CRM access to add prospects to the CRM.")
    db = ctx.db
    p = _prospect(ctx, prospect_id, lock=True)
    if p["contact_id"] is not None:                                  # repeat returns the same contact
        c = db.one("SELECT id, company_id, lifecycle_stage FROM ems.contacts WHERE id = :c", c=p["contact_id"])
        return ok({"contact_id": c["id"], "company_id": c["company_id"], "lifecycle_stage": c["lifecycle_stage"]},
                  f"{p['company_name']} is already in the CRM.", status=201)
    if _suppressed(ctx, p):
        raise ApiError("SUPPRESSED_CONTACT", "This domain asked not to be contacted.")
    owner = body.owner_id or ctx.user_id
    if not db.scalar("SELECT 1 FROM ems.memberships WHERE user_id = :u AND status = 'active'", u=owner):
        raise ApiError("ASSIGNEE_NOT_MEMBER", "The owner is not an active member of this company.")

    company_id = db.scalar("SELECT id FROM ems.companies WHERE domain = :d", d=p["domain"])
    if company_id is None:
        company_id = uuid.uuid4()
        db.execute("INSERT INTO ems.companies (id, org_id, name, domain) VALUES (:id, :org, :n, :d)",
                   id=company_id, org=ctx.org_id, n=p["company_name"] or p["domain"], d=p["domain"])
    email = p["public_emails"][0] if p["public_emails"] else None
    contact = db.one("SELECT id, company_id, lifecycle_stage FROM ems.contacts WHERE email = :e", e=email) if email else None
    if contact is None:
        contact_id = uuid.uuid4()
        try:
            with db.savepoint():
                db.execute("INSERT INTO ems.contacts (id, org_id, company_id, name, email, lifecycle_stage, owner_id, source) "
                           "VALUES (:id, :org, :co, :n, :e, 'lead', :o, 'lead_hunter')",
                           id=contact_id, org=ctx.org_id, co=company_id, n=p["company_name"] or p["domain"], e=email, o=owner)
        except IntegrityError as exc:
            raise ApiError("VALIDATION_FAILED", "A contact with this address was added at the same moment. Reload and try again.") from exc
        contact = {"id": contact_id, "company_id": company_id, "lifecycle_stage": "lead"}
        ctx.emit("contact.created", {"contact_id": str(contact_id), "source": "lead_hunter"})
    db.execute("UPDATE ems.prospects SET status = 'promoted', contact_id = :c WHERE id = :p", c=contact["id"], p=prospect_id)
    ctx.audit("prospect.promoted", "prospect", prospect_id, ["status"])
    return ok({"contact_id": contact["id"], "company_id": contact["company_id"], "lifecycle_stage": contact["lifecycle_stage"]},
              f"{p['company_name']} added to CRM.", status=201)


# ------------------------------------------------------------------------------------------------ API-059
TEMPLATES = {
    "intro_services": ("{Offer} for {company}",
                       "Hi {company} team,\n\n{observation}{org} offers {offer} so teams like yours can focus on clients.\n\n"
                       "Would a 15-minute call next week be useful?"),
    "partnership": ("Partnership idea for {company}",
                    "Hi {company} team,\n\n{observation}We work with companies like yours on {offer} and think a partnership "
                    "could help both our clients.\n\nWould you be open to a short call?"),
    "follow_up": ("Following up: {offer} for {company}",
                  "Hi {company} team,\n\nI wanted to follow up on my earlier note about {offer}. If the timing is better later "
                  "in the year, just let me know."),
}
OPT_OUT = "If you prefer not to hear from us, reply 'unsubscribe' and we will not contact you again."


class DraftIn(Body):
    template: Literal["intro_services", "partnership", "follow_up"]
    sender_name: str = Field(min_length=1, max_length=120)
    offer: str = Field(min_length=2, max_length=120)


@router.post("/prospects/{prospect_id}/outreach-draft")
def outreach_draft(prospect_id: uuid.UUID, body: DraftIn, ctx: SessionCtx):
    ctx.require("hunter.use", "Only leadership and managers can use the Lead Hunter.")
    p = _prospect(ctx, prospect_id)
    if _suppressed(ctx, p):
        raise ApiError("SUPPRESSED_CONTACT", "This domain asked not to be contacted.")
    company = p["company_name"] or p["domain"]
    tech = (p["signals"] or {}).get("tech") or []
    fields = ["company_name", "sender_name", "offer"]
    observation = ""
    if tech:
        observation = f"I saw on your site that you work with {' and '.join(TECH_LABELS.get(t, t) for t in tech[:2])}. "
        fields.insert(1, "tech")
    subject_t, body_t = TEMPLATES[body.template]
    values = {"company": company, "offer": body.offer, "Offer": body.offer[:1].upper() + body.offer[1:], "org": ctx.org["name"],
              "observation": observation}
    text = body_t.format(**values) + f"\n\n{body.sender_name}\n{ctx.org['name']}\n\n{OPT_OUT}"
    return ok({"subject": subject_t.format(**values), "body": text, "template": body.template, "fields_used": fields,
               "send_via": "copy_to_mail_client"})


# ------------------------------------------------------------------------------------------------ API-060
class SuppressionIn(Body):
    kind: Literal["email", "domain"]
    value: str = Field(min_length=3, max_length=254)
    reason: Literal["opt_out", "bounced", "manual", "legal"]


@router.post("/suppressions", status_code=201)
def add_suppression(body: SuppressionIn, ctx: SessionCtx):
    if not (ctx.can("hunter.use") or ctx.can("crm.manage")):
        raise denied("Only leadership and managers can manage the do-not-contact list.")
    try:
        value = validate_email(body.value) if body.kind == "email" else normalize_domain(body.value)
    except ValueError:
        value = ""
    if not value or (body.kind == "domain" and not is_valid_domain(value)):
        raise invalid("Enter a valid email or domain.", {"value": f"Not a valid {body.kind}."})
    db = ctx.db
    added = db.scalar("INSERT INTO ems.suppression_list (org_id, kind, value_hash, reason) VALUES (:org, :k, :h, :r) "
                      "ON CONFLICT DO NOTHING RETURNING 1", org=ctx.org_id, k=body.kind, h=suppression.value_hash(body.kind, value), r=body.reason)
    if body.kind == "domain":
        n = db.execute("UPDATE ems.prospects SET status = 'suppressed' WHERE status <> 'suppressed' "
                       "AND (domain = :d OR domain LIKE :sub)", d=value, sub="%." + value).rowcount     # validated: no LIKE wildcards
    else:
        n = db.execute("UPDATE ems.prospects SET status = 'suppressed' WHERE status <> 'suppressed' AND :e = ANY(public_emails)",
                       e=value).rowcount
    if added:
        ctx.audit("suppression.added", "suppression", None, ["kind", "reason"])
        ctx.emit("suppression.added", {"kind": body.kind, "prospects_suppressed": n})
    return ok({"kind": body.kind, "stored_as": "sha256", "prospects_suppressed": n}, status=201)

