"""Sign-up, sign-in, sign-out, password reset and the current user (API-002..006, API-009)."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from pydantic import Field
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.auth.sessions import active_organizations, clear_session_cookies, landing_path, set_session_cookies, start_session
from app.platform import events, ratelimit
from app.platform.context import DbDep, SessionCtx, SessionUser, session_user, settings_of
from app.platform.db import Db, transaction
from app.platform.errors import ApiError, invalid
from app.platform.idempotency import HEADER as IDEMPOTENCY_HEADER
from app.platform.permissions import DASHBOARD_FOR_ROLE, permissions_for
from app.platform.requestctx import current_request_id
from app.platform.responses import ok
from app.platform.schema import Body, Email
from app.platform.security import check_password_policy, hash_password, sha256, verify_password
from app.platform.timeutil import valid_time_zone

router = APIRouter(prefix="/api/v1")


def client_ip(request: Request) -> str:
    # app.serve runs uvicorn with --proxy-headers and the required FORWARDED_ALLOW_IPS, so behind the load balancer this is the real client.
    return request.client.host if request.client else "unknown"


def _audit_for_user_orgs(db: Db, user_id: uuid.UUID, action: str) -> None:
    """User-level events (sign-in, sign-out) are audited in each company the user can enter."""
    for m in db.all("SELECT org_id, status FROM ems.user_memberships(:u)", u=user_id):
        if m["status"] == "active":
            db.set_context(m["org_id"], user_id)
            events.audit(db, m["org_id"], user_id, action, "user", user_id, request_id=current_request_id())
    db.set_context(None, None)


# ------------------------------------------------------------------------------------------------ API-002
class SignupIn(Body):
    company_name: str = Field(min_length=2, max_length=120)
    company_slug: str = Field(pattern=r"^[a-z0-9][a-z0-9-]{1,40}$")
    country: str = Field(pattern=r"^[A-Z]{2}$")
    time_zone: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    email: Email
    password: str


@router.post("/auth/signup", status_code=201)
def signup(body: SignupIn, request: Request, db: DbDep):
    settings = settings_of(request)
    ratelimit.hit(request.app.state.engine, "signup", client_ip(request))
    # Idempotency-Key is required by the contract. idempotency_keys is scoped to an existing company, which a sign-up
    # does not have yet; a replayed sign-up is still safe because the unique email and slug make it return EMAIL_IN_USE.
    if not 8 <= len(request.headers.get(IDEMPOTENCY_HEADER, "")) <= 100:
        raise invalid("Send an Idempotency-Key header of 8 to 100 characters.", {IDEMPOTENCY_HEADER: "8 to 100 characters."})
    if not valid_time_zone(body.time_zone):
        raise invalid("Choose a valid time zone.", {"time_zone": "Unknown time zone."})
    check_password_policy(body.password)

    user_id, org_id = uuid.uuid4(), uuid.uuid4()
    try:
        with db.savepoint():
            db.execute("SELECT ems.signup_company(:uid, :email, :name, :pw, NULL, :oid, :oname, :slug, :tz, :country)",
                       uid=user_id, email=body.email, name=body.name, pw=hash_password(body.password), oid=org_id,
                       oname=body.company_name, slug=body.company_slug, tz=body.time_zone, country=body.country)
    except IntegrityError as exc:
        constraint = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)
        if constraint == "users_email_key":
            raise ApiError("EMAIL_IN_USE", "An account with this email already exists. Sign in instead.", {"field": "email"}) from exc
        if constraint == "organizations_slug_key":
            raise ApiError("SLUG_TAKEN", "That company address is already taken. Try another.", {"field": "company_slug"}) from exc
        raise

    db.set_context(org_id, user_id)
    rid = current_request_id()
    events.audit(db, org_id, user_id, "org.created", "organization", org_id, request_id=rid)
    events.audit(db, org_id, user_id, "user.created", "user", user_id, request_id=rid)
    events.emit(db, org_id, "org.created", {"actor_id": str(user_id), "org_id": str(org_id)})
    session = start_session(db, user_id, remember=False)

    response = ok({"user": {"id": user_id, "name": body.name, "email": body.email},
                   "org": {"id": org_id, "name": body.company_name, "slug": body.company_slug, "setup_state": "account_created"},
                   "membership": {"role": "ceo"}, "next_step": "company_setup"}, "Company account created.", status=201)
    set_session_cookies(response, settings, session)
    return response


# ------------------------------------------------------------------------------------------------ API-003
class LoginIn(Body):
    email: Email
    password: str = Field(max_length=1024)
    remember: bool = False


@router.post("/auth/login")
def login(body: LoginIn, request: Request, db: DbDep):
    engine = request.app.state.engine
    ratelimit.hit(engine, "login", f"{body.email}|{client_ip(request)}")
    row = db.one("SELECT user_id, password_hash FROM ems.find_user_for_login(:e)", e=body.email)
    if not verify_password(row["password_hash"] if row else None, body.password):
        if row is not None:
            with transaction(engine) as audit_db:      # committed even though this request fails
                _audit_for_user_orgs(audit_db, row["user_id"], "auth.login_failed")
        raise ApiError("INVALID_CREDENTIALS", "Email or password is incorrect.")

    user_id = row["user_id"]
    session = start_session(db, user_id, body.remember)
    organizations = active_organizations(db, user_id)
    _audit_for_user_orgs(db, user_id, "auth.login_succeeded")
    db.set_context(None, user_id)                               # users policy: a user can always read their own row
    name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=user_id)

    response = ok({"user": {"id": user_id, "name": name}, "session_expires_at": session.expires_at,
                   "organizations": organizations, "redirect": landing_path(organizations)}, "Signed in.")
    set_session_cookies(response, settings_of(request), session)
    return response


# ------------------------------------------------------------------------------------------------ API-004
@router.post("/auth/logout")
def logout(request: Request, user: Annotated[SessionUser, Depends(session_user)]):
    user.db.execute("SELECT ems.revoke_session(:h)", h=user.token_hash)
    _audit_for_user_orgs(user.db, user.user_id, "auth.logout")
    response = ok({"signed_out": True})
    clear_session_cookies(response, settings_of(request))
    return response


# ------------------------------------------------------------------------------------------------ API-005
class ForgotIn(Body):
    email: Email


@router.post("/auth/password/forgot", status_code=202)
def forgot_password(body: ForgotIn, request: Request, db: DbDep):
    settings = settings_of(request)
    ratelimit.hit(request.app.state.engine, "password_forgot", body.email)
    row = db.one("SELECT user_id FROM ems.find_user_for_login(:e)", e=body.email)
    if row is not None:
        _audit_for_user_orgs(db, row["user_id"], "auth.reset_requested")
    # Reset links travel only by email. With EMAIL_PROVIDER=none (INT-003 blocked until OD-09) a token could never reach
    # its owner, so none is created; the response is identical for known and unknown emails (no account enumeration)
    # and tells the client that delivery is not configured, so the UI can show "Contact your company admin".
    return ok({"accepted": True, "email_delivery": "not_configured" if settings.email_provider == "none" else "queued"},
              "If that email has an account, a reset link is on its way.", status=202)


# ------------------------------------------------------------------------------------------------ API-006
class ResetIn(Body):
    token: str = Field(min_length=10, max_length=200)
    new_password: str


@router.post("/auth/password/reset")
def reset_password(body: ResetIn, db: DbDep):
    check_password_policy(body.new_password, "new_password")
    try:
        with db.savepoint():
            revoked = db.scalar("SELECT ems.consume_password_reset(:h, :pw)", h=sha256(body.token), pw=hash_password(body.new_password))
    except DBAPIError as exc:
        if "RESET_TOKEN_EXPIRED" in str(exc.orig):
            raise ApiError("RESET_TOKEN_EXPIRED", "This reset link has expired. Request a new one.") from exc
        raise
    return ok({"password_changed": True, "sessions_revoked": revoked}, "Password changed. Sign in again.")


# ------------------------------------------------------------------------------------------------ API-009
@router.get("/me")
def me(ctx: SessionCtx):
    user = ctx.db.one("SELECT id, name, email FROM ems.users WHERE id = :u", u=ctx.user_id)
    return ok({"user": user,
               "active_org": {"id": ctx.org_id, "name": ctx.org["name"], "role": ctx.role, "time_zone": ctx.org["time_zone"],
                              "setup_state": ctx.org["setup_state"]},
               "permissions": permissions_for(ctx.role), "dashboard": DASHBOARD_FOR_ROLE[ctx.role]})
