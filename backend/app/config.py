"""Environment configuration (spec Section 34).

The API refuses to start when a required variable is missing, or when EMAIL_PROVIDER / AI_REPHRASER name an adapter
that is not implemented: there is no fake success path (Appendix F rule 4).
"""
import ipaddress
import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlparse


class ConfigError(RuntimeError):
    pass


IMPLEMENTED_EMAIL_PROVIDERS = {"none"}      # INT-003 BLOCKED until OD-09
IMPLEMENTED_AI_REPHRASERS = {"disabled"}    # INT-006 BLOCKED until OD-06


def _require(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ConfigError(f"Required environment variable {name} is not set.")
    return value


def _bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    if raw.strip().lower() in ("true", "1", "yes"):
        return True
    if raw.strip().lower() in ("false", "0", "no"):
        return False
    raise ConfigError(f"{name} must be true or false.")


@dataclass(frozen=True)
class Settings:
    database_url: str
    app_base_url: str
    session_cookie_secure: bool
    csrf_secret: bytes
    google_client_id: str
    google_client_secret: str
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    extension_id: str
    email_provider: str
    ai_rephraser: str
    log_level: str
    forwarded_allow_ips: str            # proxies whose X-Forwarded-For uvicorn trusts (app/serve.py)

    @property
    def google_configured(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def livekit_configured(self) -> bool:
        return bool(self.livekit_url and self.livekit_api_key and self.livekit_api_secret)

    @property
    def app_origin(self) -> str:
        u = urlparse(self.app_base_url)
        return f"{u.scheme}://{u.netloc}"

    @property
    def cors_origins(self) -> list[str]:
        origins = [self.app_origin]
        if self.extension_id:
            origins.append(f"chrome-extension://{self.extension_id}")
        return origins


def _forwarded_allow_ips() -> str:
    """Client IPs (used by the per-IP rate limits) come from X-Forwarded-For only for these proxies. '*' would let any
    client spoof its address, so it is refused; unset would make every request appear to come from the load balancer."""
    raw = _require("FORWARDED_ALLOW_IPS")
    entries = [e.strip() for e in raw.split(",") if e.strip()]
    if not entries or "*" in entries:
        raise ConfigError("FORWARDED_ALLOW_IPS must list the load balancer addresses or ranges; '*' is not allowed.")
    for entry in entries:
        try:
            ipaddress.ip_network(entry, strict=False)
        except ValueError as exc:
            raise ConfigError(f"FORWARDED_ALLOW_IPS entry '{entry}' is not an IP address or range.") from exc
    return ",".join(entries)


def load_settings() -> Settings:
    csrf_secret = _require("CSRF_SECRET")
    try:
        csrf_bytes = bytes.fromhex(csrf_secret)
    except ValueError as exc:
        raise ConfigError("CSRF_SECRET must be 64 hexadecimal characters.") from exc
    if len(csrf_bytes) < 32:
        raise ConfigError("CSRF_SECRET must be 64 hexadecimal characters.")

    app_base_url = _require("APP_BASE_URL").rstrip("/")
    if urlparse(app_base_url).scheme not in ("http", "https"):
        raise ConfigError("APP_BASE_URL must be an http(s) URL.")

    email_provider = os.environ.get("EMAIL_PROVIDER", "none").strip().lower() or "none"
    if email_provider not in IMPLEMENTED_EMAIL_PROVIDERS:
        raise ConfigError(f"EMAIL_PROVIDER '{email_provider}' is not implemented (INT-003 is blocked until OD-09).")
    ai_rephraser = os.environ.get("AI_REPHRASER", "disabled").strip().lower() or "disabled"
    if ai_rephraser not in IMPLEMENTED_AI_REPHRASERS:
        raise ConfigError(f"AI_REPHRASER '{ai_rephraser}' is not implemented (INT-006 is blocked until OD-06).")

    livekit = [os.environ.get(n, "").strip() for n in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")]
    if any(livekit) and not all(livekit):
        raise ConfigError("Set all of LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET, or none of them.")
    google = [os.environ.get(n, "").strip() for n in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET")]
    if any(google) and not all(google):
        raise ConfigError("Set both GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or neither.")

    return Settings(
        database_url=_require("DATABASE_URL"),
        app_base_url=app_base_url,
        session_cookie_secure=_bool("SESSION_COOKIE_SECURE", True),
        csrf_secret=csrf_bytes,
        google_client_id=google[0],
        google_client_secret=google[1],
        livekit_url=livekit[0],
        livekit_api_key=livekit[1],
        livekit_api_secret=livekit[2],
        extension_id=os.environ.get("EXTENSION_ID", "").strip(),
        email_provider=email_provider,
        ai_rephraser=ai_rephraser,
        log_level=os.environ.get("LOG_LEVEL", "info").strip().upper() or "INFO",
        forwarded_allow_ips=_forwarded_allow_ips(),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()
