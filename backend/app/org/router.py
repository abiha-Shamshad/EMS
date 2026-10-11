"""Company setup, invitations, members and roles (API-010..016)."""
import datetime as dt
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Request
from pydantic import Field, field_validator
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.auth.sessions import set_session_cookies, start_session
from app.platform import events
from app.platform.context import DbDep, SessionCtx, SessionUser, load_org, optional_session_user, settings_of
from app.platform.db import jsonb
from app.platform.errors import ApiError, invalid, not_found, version_conflict
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.permissions import MATRIX, ROLES, TEAM, roles_with
from app.platform.requestctx import current_request_id
from app.platform.responses import ok
from app.platform.schema import Body, Email, ExpectedVersion, Money
from app.platform.security import check_password_policy, hash_password, new_token, sha256
from app.platform.serialize import money
from app.platform.timeutil import WEEKDAYS, utcnow, valid_time_zone
from app.room import service as room

router = APIRouter(prefix="/api/v1")

SETUP_ORDER = ["account_created", "company_setup_done", "team_invited", "active"]
NEXT_STEP = {"account_created": "company_setup", "company_setup_done": "invite_team", "team_invited": "invite_team", "active": "done"}
INVITE_ROLES = ("cto", "cfo", "coo", "hr", "manager", "employee")
INVITE_TTL = dt.timedelta(days=7)


def _advance_setup(ctx_db, org: dict, target: str) -> str:
    """Setup states only move forward (Section 31.1)."""
    if SETUP_ORDER.index(target) > SETUP_ORDER.index(org["setup_state"]):
        ctx_db.execute("UPDATE ems.organizations SET setup_state = :s, version = version + 1", s=target)
        return target
    return org["setup_state"]


# ------------------------------------------------------------------------------------------------ API-010
class WorkHours(Body):
    days: list[Literal["mon", "tue", "wed", "thu", "fri", "sat", "sun"]] = Field(min_length=1, max_length=7)
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    late_grace_minutes: int = Field(ge=0, le=120)

    @field_validator("days")
    @classmethod
    def _unique_days(cls, v: list[str]) -> list[str]:
        return sorted(set(v), key=WEEKDAYS.index)


class OrgSetupIn(Body):
    expected_version: ExpectedVersion
    industry: str | None = Field(default=None, max_length=120)
    size_band: Literal["1-10", "11-50", "51-200", "201-500", "500+"] | None = None
    time_zone: str | None = Field(default=None, max_length=64)
    work_hours: WorkHours | None = None
    setup_state: Literal["active"] | None = None          # "Skip for now" on the invite screen


@router.patch("/org")
def update_org(body: OrgSetupIn, ctx: SessionCtx):
    ctx.require("members.manage", "Only the CEO and HR can change company settings.")
    org = ctx.db.one("SELECT version, setup_state FROM ems.organizations FOR UPDATE")
    if org["version"] != body.expected_version:
        raise version_conflict(org["version"], "Company settings were changed by someone else. Reload and try again.")
    if body.time_zone is not None and not valid_time_zone(body.time_zone):
        raise invalid("Choose a valid time zone.", {"time_zone": "Unknown time zone."})
    if body.work_hours is not None and body.work_hours.end <= body.work_hours.start:
        raise invalid("Work must end after it starts.", {"work_hours.end": "Must be after start."})

    changes = {k: v for k, v in body.model_dump(exclude={"expected_version", "setup_state"}).items()
               if k in body.model_fields_set}
    sets = []
    for column in ("industry", "size_band", "time_zone"):
        if column in changes:
            sets.append(f"{column} = :{column}")
    if "work_hours" in changes:
        if changes["work_hours"] is None:
            raise invalid("Working hours cannot be empty.", {"work_hours": "Required."})
        sets.append("work_hours = CAST(:work_hours AS jsonb)")
        changes["work_hours"] = jsonb(changes["work_hours"])
    target = "active" if body.setup_state == "active" else "company_setup_done"
    new_state = target if SETUP_ORDER.index(target) > SETUP_ORDER.index(org["setup_state"]) else org["setup_state"]
    sets += ["setup_state = :setup_state", "version = version + 1"]
    row = ctx.db.one(f"UPDATE ems.organizations SET {', '.join(sets)} RETURNING id, setup_state, version",  # noqa: S608 - fixed column names
                     setup_state=new_state, **{k: v for k, v in changes.items()})
    fields = list(changes) + (["setup_state"] if new_state != org["setup_state"] else [])
    ctx.audit("org.updated", "organization", ctx.org_id, fields)
    ctx.emit("org.updated", {"fields": fields})
    return ok({**row, "next_step": NEXT_STEP[row["setup_state"]]}, "Company details saved.")


# ------------------------------------------------------------------------------------------------ API-011
class InviteRow(Body):
    email: Email
    role: str


class InviteIn(Body):
    invites: list[InviteRow] = Field(min_length=1, max_length=20)
    message: str | None = Field(default=None, max_length=300)


@router.post("/invitations", status_code=201)
def invite(body: InviteIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("members.manage", "Only the CEO and HR can invite people.")
    bad = {f"invites[{i}].role": ("Role 'ceo' cannot be invited; there is one CEO per company." if r.role == "ceo"
                                  else f"Choose one of: {', '.join(INVITE_ROLES)}.")
           for i, r in enumerate(body.invites) if r.role not in INVITE_ROLES}
    if bad:
        raise invalid("Check the highlighted rows.", bad)

    def handler():
        db, results, invited = ctx.db, [], 0
        for row in body.invites:
            if any(r["email"] == row.email for r in results):
                continue
            if db.scalar("SELECT 1 FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id WHERE u.email = :e", e=row.email):
                results.append({"email": row.email, "status": "already_member"})
                continue
            db.execute("UPDATE ems.invitations SET status = 'expired' WHERE email = :e AND status = 'pending' AND expires_at <= now()",
                       e=row.email)
            pending = db.one("SELECT id, expires_at FROM ems.invitations WHERE email = :e AND status = 'pending'", e=row.email)
            if pending:
                results.append({"email": row.email, "status": "already_invited", "invitation_id": pending["id"],
                                "expires_at": pending["expires_at"]})
                continue
            token, token_hash = new_token("inv")
            inv_id, expires_at = uuid.uuid4(), utcnow() + INVITE_TTL
            db.execute("INSERT INTO ems.invitations (id, org_id, email, role, token_hash, message, invited_by, expires_at) "
                       "VALUES (:id, :org, :e, :r, :h, :m, :by, :exp)",
                       id=inv_id, org=ctx.org_id, e=row.email, r=row.role, h=token_hash, m=body.message, by=ctx.user_id, exp=expires_at)
            ctx.audit("member.invited", "invitation", inv_id)
            ctx.emit("member.invited", {"invitation_id": str(inv_id), "role": row.role})
            invited += 1
            # INT-003 is blocked (EMAIL_PROVIDER=none): the inviter copies this link; nothing is reported as "sent".
            results.append({"email": row.email, "status": "invited", "invitation_id": inv_id, "expires_at": expires_at,
                            "invite_link": f"{ctx.settings.app_base_url}/invite/accept?token={token}"})
        state = _advance_setup(db, ctx.org, "team_invited") if invited else ctx.org["setup_state"]
        noun = "invitation" if invited == 1 else "invitations"
        return ok({"results": results, "email_delivery": "not_configured", "copy_links": True, "org_setup_state": state},
                  f"{invited} {noun} created.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-012
class AcceptIn(Body):
    token: str = Field(min_length=10, max_length=200)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = None


@router.post("/invitations/accept")
def accept_invitation(body: AcceptIn, request: Request, db: DbDep,
                      signed_in: Annotated[SessionUser | None, Depends(optional_session_user)]):
    token_hash = sha256(body.token)
    inv = db.one("SELECT invitation_id, org_id, email, role, status, expires_at FROM ems.resolve_invitation(:h)", h=token_hash)
    if inv is None or inv["status"] != "pending" or inv["expires_at"] <= utcnow():
        raise ApiError("INVITATION_INVALID", "This invitation has expired or was already used. Ask for a new one.")

    session = None
    if signed_in is not None:
        user_id = signed_in.user_id
    else:
        if db.one("SELECT user_id FROM ems.find_user_for_login(:e)", e=inv["email"]):
            raise ApiError("AUTHENTICATION_REQUIRED", "Sign in with your existing account to accept this invitation.")
        if not body.name or not body.password:
            raise invalid("Enter your name and a password.", {"name": "Required.", "password": "Required."})
        check_password_policy(body.password)
        user_id = db.scalar("SELECT ems.create_user(:id, :e, :n, :pw, NULL)",
                            id=uuid.uuid4(), e=inv["email"], n=body.name, pw=hash_password(body.password))
    try:
        with db.savepoint():
            org_id = db.scalar("SELECT ems.accept_invitation(:h, :u)", h=token_hash, u=user_id)
    except IntegrityError as exc:                       # already a member of this company
        raise ApiError("INVITATION_INVALID", "You are already a member of this company.") from exc
    except DBAPIError as exc:
        if "INVITATION_EMAIL_MISMATCH" in str(exc.orig):
            raise ApiError("INVITATION_EMAIL_MISMATCH", "This invitation was sent to a different email address.") from exc
        if "INVITATION_INVALID" in str(exc.orig):
            raise ApiError("INVITATION_INVALID", "This invitation has expired or was already used. Ask for a new one.") from exc
        raise
    if signed_in is None:
        session = start_session(db, user_id, remember=False)

    db.set_context(org_id, user_id)
    org = load_org(db)
    _advance_setup(db, org, "active")                   # the first accepted invitation activates the company
    inviter = db.scalar("SELECT invited_by FROM ems.invitations WHERE id = :i", i=inv["invitation_id"])
    events.audit(db, org_id, user_id, "member.joined", "membership", user_id, request_id=current_request_id())
    events.emit(db, org_id, "member.joined", {"actor_id": str(user_id), "user_id": str(user_id), "role": inv["role"],
                                              "invited_by": str(inviter)})
    response = ok({"org": {"id": org_id, "name": org["name"]}, "membership": {"role": inv["role"]}, "next_step": "install_extension"},
                  f"Welcome to {org['name']}.")
    if session is not None:
        set_session_cookies(response, settings_of(request), session)
    return response


# ------------------------------------------------------------------------------------------------ API-013
@router.get("/members")
def list_members(ctx: SessionCtx, role: str | None = None, status: Literal["active", "deactivated"] | None = None,
                 department: str | None = None, cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    limit = clamp_limit(limit)
    after = decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT m.user_id, u.name, m.role, m.title, m.department, m.status, m.manager_id, m.cost_rate, m.version "
        "FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id "
        "WHERE (CAST(:role AS text) IS NULL OR m.role = :role) AND (CAST(:status AS text) IS NULL OR m.status = :status) "
        "AND (CAST(:dept AS text) IS NULL OR m.department = :dept) "
        "AND (CAST(:a_name AS text) IS NULL OR (u.name, m.user_id) > (:a_name, CAST(:a_id AS uuid))) "
        "ORDER BY u.name, m.user_id LIMIT :lim",
        role=role, status=status, dept=department, a_name=after[0] if after else None, a_id=after[1] if after else None,
        lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["name"], str(r["user_id"])])
    show_cost = ctx.can("finance.manage")
    items = []
    for r in rows:
        item = {k: r[k] for k in ("user_id", "name", "role", "title", "department", "status", "version")}
        if r["manager_id"]:
            item["manager_id"] = r["manager_id"]
        if show_cost:
            item["cost_rate"] = money(r["cost_rate"])
        items.append(item)
    return ok({"items": items, "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-014
class MemberUpdateIn(Body):
    expected_version: ExpectedVersion
    role: Literal["ceo", "cto", "cfo", "coo", "hr", "manager", "employee"] | None = None
    title: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    manager_id: uuid.UUID | None = None
    cost_rate: Money | None = None


@router.patch("/members/{user_id}")
def update_member(user_id: uuid.UUID, body: MemberUpdateIn, ctx: SessionCtx):
    fields = body.model_fields_set - {"expected_version"}
    if not fields:
        raise invalid("Nothing to change.")
    if "cost_rate" in fields:
        ctx.require("finance.manage", "Only the CEO and CFO can set cost rates.")
    if fields - {"cost_rate"}:
        ctx.require("members.manage", "Only the CEO and HR can change members.")
    m = ctx.db.one("SELECT user_id, role, status, version FROM ems.memberships WHERE user_id = :u FOR UPDATE", u=user_id)
    if m is None:
        raise not_found("Member")
    if m["version"] != body.expected_version:
        raise version_conflict(m["version"])
    if "role" in fields and (body.role == "ceo") != (m["role"] == "ceo"):
        raise ApiError("ONE_CEO_ONLY", "A company has exactly one CEO. Transfer the CEO role from the CEO's own settings.")
    if "role" in fields and body.role is None:
        raise invalid("Choose a role.", {"role": "Required."})
    if body.manager_id is not None:
        if body.manager_id == user_id:
            raise invalid("A person cannot be their own manager.", {"manager_id": "Choose someone else."})
        if not ctx.db.scalar("SELECT 1 FROM ems.memberships WHERE user_id = :u AND status = 'active'", u=body.manager_id):
            raise ApiError("ASSIGNEE_NOT_MEMBER", "The manager is not an active member of this company.")

    values = body.model_dump(include=fields)
    sets = ", ".join(f"{f} = :{f}" for f in sorted(fields))
    row = ctx.db.one(f"UPDATE ems.memberships SET {sets}, version = version + 1 WHERE user_id = :uid "  # noqa: S608 - fixed names
                     "RETURNING user_id, role, title, department, manager_id, version", uid=user_id, **values)
    ctx.audit("member.updated", "membership", user_id, fields)
    if fields & {"role", "manager_id"}:
        ctx.emit("member.role_changed", {"user_id": str(user_id), "role": row["role"],
                                         "manager_id": str(row["manager_id"]) if row["manager_id"] else None})
    data = {"user_id": row["user_id"], "version": row["version"]}
    data.update({f: row[f] for f in ("role", "title", "department", "manager_id") if f in fields})
    if "cost_rate" in fields:
        data["cost_rate"] = money(body.cost_rate)
    return ok(data, "Member updated.")


# ------------------------------------------------------------------------------------------------ API-015
class DeactivateIn(Body):
    reassign_to: uuid.UUID | None = None
    reason: str | None = Field(default=None, max_length=500)    # shown in the UI flow; audit stores field names only


@router.post("/members/{user_id}/deactivate")
def deactivate_member(user_id: uuid.UUID, body: DeactivateIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("members.manage", "Only the CEO and HR can deactivate members.")

    def handler():
        db = ctx.db
        m = db.one("SELECT role, status FROM ems.memberships WHERE user_id = :u FOR UPDATE", u=user_id)
        if m is None:
            raise not_found("Member")
        if m["role"] == "ceo":
            raise ApiError("CANNOT_DEACTIVATE_CEO", "The CEO cannot be deactivated.")
        if m["status"] == "deactivated":
            return ok({"user_id": user_id, "status": "deactivated", "tasks_reassigned": 0, "deals_reassigned": 0,
                       "work_session_closed": False})
        to = body.reassign_to
        if to is not None and (to == user_id or not db.scalar(
                "SELECT 1 FROM ems.memberships WHERE user_id = :u AND status = 'active'", u=to)):
            raise ApiError("ASSIGNEE_NOT_MEMBER", "Reassign work to an active member other than the person leaving.")
        owns_required = db.scalar(
            "SELECT (SELECT count(*) FROM ems.deals WHERE owner_id = :u AND stage NOT IN ('won','lost')) + "
            "(SELECT count(*) FROM ems.projects WHERE owner_id = :u AND status NOT IN ('completed','cancelled'))", u=user_id)
        if owns_required and to is None:
            raise invalid("This person owns open deals or projects. Choose who takes them over.",
                          {"reassign_to": "Required while they own open deals or projects."})

        tasks = db.execute("UPDATE ems.tasks SET assignee_id = :to, version = version + 1 "
                           "WHERE assignee_id = :u AND status <> 'done'", to=to, u=user_id).rowcount
        deals = db.execute("UPDATE ems.deals SET owner_id = :to, version = version + 1 "
                           "WHERE owner_id = :u AND stage NOT IN ('won','lost')", to=to, u=user_id).rowcount
        db.execute("UPDATE ems.projects SET owner_id = :to, version = version + 1 "
                   "WHERE owner_id = :u AND status NOT IN ('completed','cancelled')", to=to, u=user_id)
        db.execute("UPDATE ems.contacts SET owner_id = :to, version = version + 1 WHERE owner_id = :u", to=to, u=user_id)
        db.execute("UPDATE ems.memberships SET manager_id = NULL, version = version + 1 WHERE manager_id = :u", u=user_id)

        session = room.open_session(db, user_id, lock=True)
        if session is not None:
            room.close_session(db, session, utcnow(), "closed")
        db.execute("UPDATE ems.extension_tokens SET revoked_at = now() WHERE user_id = :u AND revoked_at IS NULL", u=user_id)
        db.execute("UPDATE ems.stream_views SET ended_at = now() WHERE ended_at IS NULL AND (subject_user_id = :u OR viewer_id = :u)",
                   u=user_id)
        db.execute("UPDATE ems.memberships SET status = 'deactivated', version = version + 1 WHERE user_id = :u", u=user_id)
        ctx.audit("member.deactivated", "membership", user_id, ["status"])
        ctx.emit("member.deactivated", {"user_id": str(user_id), "reassign_to": str(to) if to else None})
        return ok({"user_id": user_id, "status": "deactivated", "tasks_reassigned": tasks, "deals_reassigned": deals,
                   "work_session_closed": session is not None})

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-016
@router.get("/roles/permissions")
def permission_matrix(ctx: SessionCtx):
    return ok({"roles": list(ROLES),
               "matrix": {p: roles_with(p) for p in MATRIX},
               "team_scope": {p: [r for r, s in roles.items() if s == TEAM] for p, roles in MATRIX.items()
                              if TEAM in roles.values()}})

