"""Google sign-in, OpenID Connect authorization-code flow with state, nonce and S256 PKCE (API-007/008, Section 7.3).

Endpoints come from Google's discovery document (EV-006). The ID token is validated for signature (jwks_uri), iss,
aud, exp and nonce; users are identified by `sub`, never by email (EV-007). Google never creates a company.
"""
import base64
import hashlib
import hmac
import json
import re
import secrets
import threading
import time
import uuid
from typing import Annotated
from urllib.parse import urlencode

import httpx
import jwt
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.auth.sessions import active_organizations, landing_path, set_session_cookies, start_session
from app.config import Settings
from app.platform import events
from app.platform.context import DbDep, SessionUser, optional_session_user, settings_of
from app.platform.db import Db
from app.platform.errors import ApiError
from app.platform.requestctx import current_request_id
from app.platform.security import sign

router = APIRouter(prefix="/api/v1/auth/google")

DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"
ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
STATE_COOKIE, STATE_TTL = "ems_oauth", 600
CALLBACK_PATH = "/api/v1/auth/google/callback"

_discovery: dict = {"doc": None, "expires": 0.0}
_jwk_clients: dict[str, jwt.PyJWKClient] = {}
_lock = threading.Lock()


def _not_configured() -> ApiError:
    return ApiError("GOOGLE_NOT_CONFIGURED", "Google sign-in is not available. Use email and password.")


def _state_error() -> ApiError:
    return ApiError("STATE_MISMATCH", "Google sign-in could not be verified. Start again.")


def discovery() -> dict:
    """Discovery document, cached per its Cache-Control max-age."""
    with _lock:
        if _discovery["doc"] is None or time.monotonic() >= _discovery["expires"]:
            resp = httpx.get(DISCOVERY_URL, timeout=10.0)
            resp.raise_for_status()
            match = re.search(r"max-age=(\d+)", resp.headers.get("cache-control", ""))
            _discovery["doc"] = resp.json()
            _discovery["expires"] = time.monotonic() + (int(match.group(1)) if match else 3600)
        return _discovery["doc"]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _pack_state(settings: Settings, payload: dict) -> str:
    raw = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{raw}.{sign(settings.csrf_secret, raw.encode())}"


def _unpack_state(settings: Settings, cookie: str | None) -> dict:
    if not cookie or "." not in cookie:
        raise _state_error()
    raw, sig = cookie.rsplit(".", 1)
    if not hmac.compare_digest(sign(settings.csrf_secret, raw.encode()), sig):
        raise _state_error()
    payload = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    if payload.get("exp", 0) < time.time():
        raise _state_error()
    return payload


def _safe_return_to(value: str | None) -> str | None:
    """Only same-site relative paths: blocks open redirects such as //evil.example or /\\evil.example."""
    if value and value.startswith("/") and not value.startswith("//") and "\\" not in value and len(value) <= 500:
        return value
    return None


# ------------------------------------------------------------------------------------------------ API-007
@router.get("/start")
def google_start(request: Request, return_to: str | None = None):
    settings = settings_of(request)
    if not settings.google_configured:
        raise _not_configured()
    state, nonce, verifier = secrets.token_urlsafe(24), secrets.token_urlsafe(24), secrets.token_urlsafe(48)
    challenge = _b64(hashlib.sha256(verifier.encode()).digest())
    query = urlencode({"response_type": "code", "client_id": settings.google_client_id, "scope": "openid email profile",
                       "redirect_uri": settings.app_base_url + CALLBACK_PATH, "state": state, "nonce": nonce,
                       "code_challenge": challenge, "code_challenge_method": "S256"})
    response = RedirectResponse(f"{discovery()['authorization_endpoint']}?{query}", status_code=302)
    cookie = _pack_state(settings, {"state": state, "nonce": nonce, "verifier": verifier,
                                    "return_to": _safe_return_to(return_to), "exp": int(time.time()) + STATE_TTL})
    response.set_cookie(STATE_COOKIE, cookie, max_age=STATE_TTL, httponly=True, secure=settings.session_cookie_secure,
                        samesite="lax", path="/api/v1/auth/google")
    return response


def _verify_id_token(settings: Settings, doc: dict, id_token: str, nonce: str) -> dict:
    jwks_uri = doc["jwks_uri"]
    client = _jwk_clients.setdefault(jwks_uri, jwt.PyJWKClient(jwks_uri))
    try:
        key = client.get_signing_key_from_jwt(id_token).key
        claims = jwt.decode(id_token, key, algorithms=["RS256"], audience=settings.google_client_id,
                            options={"require": ["exp", "iat", "iss", "aud", "sub"], "verify_iss": False})
    except jwt.PyJWTError as exc:
        raise _state_error() from exc
    if claims["iss"] not in ISSUERS or not hmac.compare_digest(str(claims.get("nonce", "")), nonce):
        raise _state_error()
    return claims


def _resolve_user(db: Db, claims: dict, signed_in: SessionUser | None) -> uuid.UUID:
    sub = claims["sub"]
    row = db.one("SELECT user_id FROM ems.find_user_by_google(:s)", s=sub)
    if row:
        return row["user_id"]
    email = str(claims.get("email", "")).lower()
    if claims.get("email_verified") is not True or not email:
        raise ApiError("GOOGLE_ACCOUNT_NOT_LINKED", "No EMS account uses this Google account. Ask your company admin for an invitation.")
    existing = db.one("SELECT user_id FROM ems.find_user_for_login(:e)", e=email)
    signed_in_email = None
    if signed_in is not None:
        db.set_context(None, signed_in.user_id)
        signed_in_email = db.scalar("SELECT email FROM ems.users WHERE id = :u", u=signed_in.user_id)
        db.set_context(None, None)
    invited = db.scalar("SELECT ems.pending_invitation_exists(:e)", e=email)

    if existing and (invited or (signed_in and signed_in_email == email and signed_in.user_id == existing["user_id"])):
        if not db.scalar("SELECT ems.link_google(:u, :s)", u=existing["user_id"], s=sub):
            raise ApiError("GOOGLE_ACCOUNT_NOT_LINKED", "This EMS account is already linked to a different Google account.")
        return existing["user_id"]
    if not existing and invited:
        name = str(claims.get("name") or email.split("@", 1)[0])[:120]
        return db.scalar("SELECT ems.create_user(:id, :e, :n, NULL, :s)", id=uuid.uuid4(), e=email, n=name, s=sub)
    raise ApiError("GOOGLE_ACCOUNT_NOT_LINKED", "No EMS account uses this Google account. Ask your company admin for an invitation.")


# ------------------------------------------------------------------------------------------------ API-008
@router.get("/callback")
def google_callback(request: Request, db: DbDep, signed_in: Annotated[SessionUser | None, Depends(optional_session_user)],
                    code: str | None = None, state: str | None = None):
    settings = settings_of(request)
    if not settings.google_configured:
        raise _not_configured()
    saved = _unpack_state(settings, request.cookies.get(STATE_COOKIE))
    if not code or not state or not hmac.compare_digest(state, saved["state"]):
        raise _state_error()

    doc = discovery()
    try:
        token_resp = httpx.post(doc["token_endpoint"], timeout=10.0, data={
            "grant_type": "authorization_code", "code": code, "code_verifier": saved["verifier"],
            "client_id": settings.google_client_id, "client_secret": settings.google_client_secret,
            "redirect_uri": settings.app_base_url + CALLBACK_PATH})
    except httpx.HTTPError as exc:
        raise _state_error() from exc
    if token_resp.status_code != 200 or "id_token" not in token_resp.json():
        raise _state_error()
    claims = _verify_id_token(settings, doc, token_resp.json()["id_token"], saved["nonce"])

    user_id = _resolve_user(db, claims, signed_in)
    session = start_session(db, user_id, remember=False)
    organizations = active_organizations(db, user_id)
    for org in organizations:
        db.set_context(org["id"], user_id)
        events.audit(db, org["id"], user_id, "auth.login_succeeded", "user", user_id, ["method_google"], current_request_id())
    db.set_context(None, None)

    response = RedirectResponse(saved.get("return_to") or landing_path(organizations), status_code=302)
    set_session_cookies(response, settings, session)
    response.delete_cookie(STATE_COOKIE, path="/api/v1/auth/google")
    return response
