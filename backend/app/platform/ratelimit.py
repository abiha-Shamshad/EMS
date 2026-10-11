"""PostgreSQL rate limits (spec Section 19.3, DEC-004).

Each hit is committed on its own connection, so a request that later fails (a wrong password, for example) still counts.
"""
from sqlalchemy import Engine, text

from app.platform.errors import ApiError
from app.platform.security import sha256

# name -> (limit, window seconds)
LIMITS = {
    "login": (10, 15 * 60),          # per email + IP
    "signup": (5, 60 * 60),          # per IP
    "password_forgot": (3, 60 * 60),  # per email
    "hr_agent": (30, 60),            # per user
    "heartbeat": (4, 60),            # per work session
}


def hit(engine: Engine, name: str, subject: str) -> None:
    limit, window = LIMITS[name]
    with engine.connect() as conn, conn.begin():
        retry_after = conn.execute(text("SELECT ems.rate_limit_hit(:bucket, :limit, :window)"),
                                   {"bucket": sha256(f"{name}|{subject}"), "limit": limit, "window": window}).scalar()
    if retry_after:
        raise ApiError("RATE_LIMITED", "Too many requests. Try again later.", headers={"Retry-After": str(retry_after)})
