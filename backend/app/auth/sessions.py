"""Web sessions (DEC-012): opaque 32-byte tokens, SHA-256 stored, 12 hours or 30 days with "Keep me signed in"."""
import datetime as dt
import uuid
from dataclasses import dataclass

from fastapi import Response

from app.config import Settings
from app.platform.context import CSRF_COOKIE, SESSION_COOKIE
from app.platform.db import Db
from app.platform.permissions import DASHBOARD_FOR_ROLE
from app.platform.security import csrf_token, new_token


@dataclass(frozen=True)
class NewSession:
    token: str
    token_hash: bytes
    remember: bool
    expires_at: dt.datetime


def start_session(db: Db, user_id: uuid.UUID, remember: bool) -> NewSession:
    token, token_hash = new_token("ses")
    expires_at = db.scalar("SELECT ems.create_session(:id, :usr, :h, :remember)",
                           id=uuid.uuid4(), usr=user_id, h=token_hash, remember=remember)
    return NewSession(token, token_hash, remember, expires_at)


def set_session_cookies(response: Response, settings: Settings, session: NewSession) -> None:
    """ems_session is HttpOnly; ems_csrf is readable by the web app, which echoes it in X-CSRF-Token."""
    max_age = int((session.expires_at - dt.datetime.now(dt.UTC)).total_seconds()) if session.remember else None
    common = {"secure": settings.session_cookie_secure, "samesite": "lax", "path": "/", "max_age": max_age}
    response.set_cookie(SESSION_COOKIE, session.token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE, csrf_token(settings.csrf_secret, session.token_hash), httponly=False, **common)


def clear_session_cookies(response: Response, settings: Settings) -> None:
    for name in (SESSION_COOKIE, CSRF_COOKIE):
        response.delete_cookie(name, path="/", secure=settings.session_cookie_secure, samesite="lax")


def active_organizations(db: Db, user_id: uuid.UUID) -> list[dict]:
    """Companies the user can enter, with names. Names are read under each company's own RLS context."""
    out = []
    for m in db.all("SELECT org_id, role, status FROM ems.user_memberships(:u) ORDER BY org_id", u=user_id):
        if m["status"] != "active":
            continue
        db.set_context(m["org_id"], user_id)
        name = db.scalar("SELECT name FROM ems.organizations")
        out.append({"id": m["org_id"], "name": name, "role": m["role"]})
    db.set_context(None, None)
    return out


def landing_path(organizations: list[dict]) -> str:
    if len(organizations) == 1:
        return f"/dashboards/{DASHBOARD_FOR_ROLE[organizations[0]['role']]}"
    return "/select-company" if organizations else "/no-company"
