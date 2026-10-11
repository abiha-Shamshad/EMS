"""Tokens, password hashing and CSRF (spec Sections 7.3 and 32).

Sessions, invitations, password resets and extension tokens are 32 random bytes; only SHA-256 hashes are stored.
"""
import hashlib
import hmac
import secrets
from functools import lru_cache
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.platform.errors import invalid

_hasher = PasswordHasher()          # argon2-cffi 25.1.0 defaults: argon2id
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(24))

PASSWORD_MIN, PASSWORD_MAX = 12, 128
_COMMON_PASSWORDS_FILE = Path(__file__).resolve().parents[1] / "auth" / "common_passwords.txt"


def sha256(value: str) -> bytes:
    return hashlib.sha256(value.encode("utf-8")).digest()


def new_token(prefix: str) -> tuple[str, bytes]:
    """Return (token for the client, SHA-256 digest for the database)."""
    token = f"{prefix}_{secrets.token_urlsafe(32)}"
    return token, sha256(token)


@lru_cache(maxsize=1)
def _common_passwords() -> frozenset[str]:
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line.strip() for line in lines if line.strip() and not line.startswith("#"))


def check_password_policy(password: str, field: str = "password") -> None:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise invalid("Use a password of 12 to 128 characters.", {field: "12 to 128 characters."})
    if password.lower() in _common_passwords():
        raise invalid("That password is too common. Choose another.", {field: "Too common."})


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Constant-shape check: unknown users and Google-only users still pay for one argon2 verify (API-003)."""
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def csrf_token(secret: bytes, session_token_hash: bytes) -> str:
    """Double-submit token bound to the session: HMAC(CSRF_SECRET, sha256(session token))."""
    return hmac.new(secret, session_token_hash, hashlib.sha256).hexdigest()


def csrf_valid(secret: bytes, session_token_hash: bytes, presented: str | None) -> bool:
    return bool(presented) and hmac.compare_digest(csrf_token(secret, session_token_hash), presented)


def sign(secret: bytes, payload: bytes) -> str:
    return hmac.new(secret, payload, hashlib.sha256).hexdigest()
