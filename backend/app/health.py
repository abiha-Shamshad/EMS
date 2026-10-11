"""API-001 Health and readiness. Outside the envelope (Section 19.1); details only for private-network callers."""
import ipaddress
import time
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

VERSION = "1.0.0"
LIVEKIT_CHECK_TTL = 15.0           # seconds; the load balancer polls often and must not hammer the media server
router = APIRouter()
_livekit_cache: dict[str, tuple[float, str]] = {}


def _is_private(host: str | None) -> bool:
    try:
        return host is not None and not ipaddress.ip_address(host).is_global
    except ValueError:
        return False


def _livekit_state(livekit_url: str) -> str:
    if not livekit_url:
        return "not_configured"
    cached = _livekit_cache.get(livekit_url)
    if cached and time.monotonic() - cached[0] < LIVEKIT_CHECK_TTL:
        return cached[1]
    u = urlparse(livekit_url)
    probe = f"{'https' if u.scheme in ('wss', 'https') else 'http'}://{u.netloc}/"
    try:
        state = "ok" if httpx.get(probe, timeout=2.0).status_code < 500 else "unavailable"
    except httpx.HTTPError:
        state = "unavailable"
    _livekit_cache[livekit_url] = (time.monotonic(), state)
    return state


@router.get("/health", include_in_schema=False)
def health(request: Request) -> JSONResponse:
    checks: dict[str, object] = {}
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            checks["postgres"] = "ok"
            checks["worker_lag_seconds"] = conn.execute(text("SELECT ems.outbox_lag_seconds()")).scalar()
    except Exception:  # noqa: BLE001 - any database failure means "not ready"
        checks = {"postgres": "unavailable"}
        return JSONResponse({"status": "unavailable", "checks": checks, "version": VERSION}, status_code=503)

    checks = {"postgres": "ok", "livekit": _livekit_state(request.app.state.settings.livekit_url),
              "worker_lag_seconds": checks["worker_lag_seconds"]}
    status = "ready" if checks["livekit"] == "ok" else "degraded"
    body: dict[str, object] = {"status": status, "version": VERSION}
    if _is_private(request.client.host if request.client else None):
        body = {"status": status, "checks": checks, "version": VERSION}
    return JSONResponse(body)
