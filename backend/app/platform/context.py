"""Request pipeline (spec Section 7.1).

1. Resolve the session cookie (ems.resolve_session) or the extension bearer token (ems.resolve_extension_token).
2. Choose the organization: X-Org-Id if sent, else the only active membership; several -> 403 ORG_NOT_SELECTED.
3. Load the membership; deactivated -> 423 MEMBER_DEACTIVATED.
4. In the request transaction (as ems_app): set_config('app.org_id'/'app.user_id', ..., true).
5. Route handlers check permissions with `ctx.require(...)`.

The transaction dependency uses scope="function", so the commit happens before the response is sent: a client never
sees success for a write that did not commit.
"""
import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Annotated, Any

from fastapi import Depends, Request

from app.config import Settings
from app.platform import events, permissions
from app.platform.db import Db
from app.platform.errors import ApiError, denied
from app.platform.requestctx import current_request_id, set_log_field
from app.platform.security import csrf_valid, sha256
from app.platform.timeutil import Calendar

SESSION_COOKIE, CSRF_COOKIE, CSRF_HEADER = "ems_session", "ems_csrf", "X-CSRF-Token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
ORG_COLUMNS = ("id, name, slug, time_zone, country, industry, size_band, setup_state, version, work_hours, "
               "live_view_enabled, room_policy_version, daily_break_allowance_minutes, base_currency")


def get_db(request: Request) -> Iterator[Db]:
    with request.app.state.engine.connect() as conn:
        tx = conn.begin()
        try:
            yield Db(conn)
        except BaseException:
            tx.rollback()
            raise
        else:
            tx.commit()


DbDep = Annotated[Db, Depends(get_db, scope="function")]


def settings_of(request: Request) -> Settings:
    return request.app.state.settings


@dataclass
class SessionUser:
    """A signed-in user before any organization is chosen (logout, invitation acceptance)."""
    db: Db
    user_id: uuid.UUID
    token_hash: bytes


@dataclass
class Ctx:
    db: Db
    settings: Settings
    user_id: uuid.UUID
    org_id: uuid.UUID
    role: str
    via: str                                  # "session" | "extension"
    org: dict[str, Any]
    ext_session_id: uuid.UUID | None = None   # the work session an extension token was issued for
    request_id: str = field(default_factory=current_request_id)
    _team: set[uuid.UUID] | None = None

    # ---------------------------------------------------------------- permissions
    def scope(self, permission: str) -> str | None:
        return permissions.scope(self.role, permission)

    def can(self, permission: str) -> bool:
        return self.scope(permission) is not None

    def require(self, permission: str, message: str | None = None) -> str:
        s = self.scope(permission)
        if s is None:
            raise denied(message or "Your role does not allow this action.")
        return s

    def team_ids(self) -> set[uuid.UUID]:
        """Active direct reports of the caller (the 'team only' scope of Section 7.2)."""
        if self._team is None:
            rows = self.db.all("SELECT user_id FROM ems.memberships WHERE manager_id = :me AND status = 'active'", me=self.user_id)
            self._team = {r["user_id"] for r in rows}
        return self._team

    def covers(self, permission: str, user_id: uuid.UUID) -> bool:
        """True when the caller holds `permission` for this specific person."""
        s = self.scope(permission)
        return s == permissions.ALL or (s == permissions.TEAM and user_id in self.team_ids())

    # ---------------------------------------------------------------- company calendar
    @property
    def calendar(self) -> Calendar:
        return Calendar(self.org["time_zone"], self.org["work_hours"])

    # ---------------------------------------------------------------- audit / outbox / notifications
    def audit(self, action: str, record_type: str | None = None, record_id: Any = None, changed_fields=None) -> None:
        events.audit(self.db, self.org_id, self.user_id, action, record_type, record_id, changed_fields, self.request_id)

    def emit(self, routing_key: str, payload: dict[str, Any]) -> uuid.UUID:
        return events.emit(self.db, self.org_id, routing_key, {"actor_id": str(self.user_id), **payload})

    def notify(self, user_ids, kind: str, title: str, ref_type: str | None = None, ref_id: Any = None) -> int:
        return events.notify(self.db, self.org_id, user_ids, kind, title, ref_type, ref_id)


# -------------------------------------------------------------------- principal resolution
def resolve_session(request: Request, db: Db) -> tuple[uuid.UUID, bytes] | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    token_hash = sha256(token)
    row = db.one("SELECT user_id FROM ems.resolve_session(:h)", h=token_hash)
    if row is None:
        return None
    if request.method in UNSAFE_METHODS and not csrf_valid(settings_of(request).csrf_secret, token_hash,
                                                            request.headers.get(CSRF_HEADER)):
        raise denied("Security check failed. Reload the page and try again.")
    return row["user_id"], token_hash


def _bearer(request: Request) -> str | None:
    header = request.headers.get("Authorization", "")
    scheme, _, value = header.partition(" ")
    return value.strip() if scheme.lower() == "bearer" and value.strip() else None


def load_org(db: Db) -> dict[str, Any]:
    org = db.one(f"SELECT {ORG_COLUMNS} FROM ems.organizations")  # noqa: S608 - constant column list; RLS returns one row
    if org is None:
        raise ApiError("AUTHORIZATION_DENIED", "Company not found for this session.")
    return org


def _choose_org(request: Request, memberships: list[dict[str, Any]]) -> dict[str, Any]:
    requested = request.headers.get("X-Org-Id")
    if requested:
        try:
            wanted = uuid.UUID(requested)
        except ValueError as exc:
            raise ApiError("VALIDATION_FAILED", "X-Org-Id must be a company ID.") from exc
        match = next((m for m in memberships if m["org_id"] == wanted), None)
        if match is None:
            raise denied("You are not a member of that company.")
        return match
    active = [m for m in memberships if m["status"] == "active"]
    if len(active) == 1:
        return active[0]
    if len(active) > 1:
        raise ApiError("ORG_NOT_SELECTED", "You belong to several companies. Choose one to continue.",
                       {"organizations": [str(m["org_id"]) for m in active]})
    if memberships:
        raise ApiError("MEMBER_DEACTIVATED", "Your access to this company has been removed.")
    raise denied("You are not a member of any company.")


def build_ctx(request: Request, db: Db, *, allow_session: bool, allow_extension: bool) -> Ctx:
    settings = settings_of(request)
    ext_token = _bearer(request) if allow_extension else None
    ext_session_id = None
    if ext_token:
        row = db.one("SELECT org_id, user_id, session_id FROM ems.resolve_extension_token(:h)", h=sha256(ext_token))
        if row is None:
            raise ApiError("AUTHENTICATION_REQUIRED", "The extension sign-in has expired. Check in again.")
        user_id, ext_session_id, via = row["user_id"], row["session_id"], "extension"
        memberships = [m for m in db.all("SELECT org_id, role, status FROM ems.user_memberships(:u)", u=user_id)
                       if m["org_id"] == row["org_id"]]
        membership = memberships[0] if memberships else None
    else:
        principal = resolve_session(request, db) if allow_session else None
        if principal is None:
            raise ApiError("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again.")
        user_id, via = principal[0], "session"
        membership = _choose_org(request, db.all("SELECT org_id, role, status FROM ems.user_memberships(:u)", u=user_id))
    if membership is None:
        raise ApiError("AUTHENTICATION_REQUIRED", "Your session has expired. Sign in again.")
    if membership["status"] != "active":
        raise ApiError("MEMBER_DEACTIVATED", "Your access to this company has been removed.")

    db.set_context(membership["org_id"], user_id)
    set_log_field("org_id", str(membership["org_id"]))
    set_log_field("user_id", str(user_id))
    return Ctx(db=db, settings=settings, user_id=user_id, org_id=membership["org_id"], role=membership["role"],
               via=via, org=load_org(db), ext_session_id=ext_session_id)


def session_ctx(request: Request, db: DbDep) -> Ctx:
    return build_ctx(request, db, allow_session=True, allow_extension=False)


def session_or_extension_ctx(request: Request, db: DbDep) -> Ctx:
    return build_ctx(request, db, allow_session=True, allow_extension=True)


def extension_ctx(request: Request, db: DbDep) -> Ctx:
    return build_ctx(request, db, allow_session=False, allow_extension=True)


def session_user(request: Request, db: DbDep) -> SessionUser:
    principal = resolve_session(request, db)
    if principal is None:
        raise ApiError("AUTHENTICATION_REQUIRED", "You are not signed in.")
    set_log_field("user_id", str(principal[0]))
    return SessionUser(db=db, user_id=principal[0], token_hash=principal[1])


def optional_session_user(request: Request, db: DbDep) -> SessionUser | None:
    principal = resolve_session(request, db)
    return SessionUser(db=db, user_id=principal[0], token_hash=principal[1]) if principal else None


SessionCtx = Annotated[Ctx, Depends(session_ctx)]
EitherCtx = Annotated[Ctx, Depends(session_or_extension_ctx)]
ExtensionCtx = Annotated[Ctx, Depends(extension_ctx)]
