"""Do-not-contact checks for CRM writes (API-045 SUPPRESSED_CONTACT; spec Section 14.1 rule 6).
Only the SHA-256 of the normalized value is stored. Adding entries (API-060) belongs to the Lead Hunter task (TASK-012)."""
import hashlib

from app.platform.db import Db
from app.platform.schema import normalize_domain


def normalize(kind: str, value: str) -> str:
    return value.strip().lower() if kind == "email" else normalize_domain(value)


def value_hash(kind: str, value: str) -> bytes:
    return hashlib.sha256(normalize(kind, value).encode("utf-8")).digest()


def is_suppressed(db: Db, *, email: str | None = None, domain: str | None = None) -> bool:
    """True if the email, its domain, or the given domain is on the list."""
    hashes = []
    if email:
        hashes.append(("email", value_hash("email", email)))
        hashes.append(("domain", value_hash("domain", email.rsplit("@", 1)[-1])))
    if domain:
        hashes.append(("domain", value_hash("domain", domain)))
    return any(db.scalar("SELECT 1 FROM ems.suppression_list WHERE kind = :k AND value_hash = :h", k=k, h=h) for k, h in hashes)
