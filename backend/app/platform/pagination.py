"""Opaque cursor pagination (spec Section 19.2): `limit` (default 25, max 100) and `next_cursor`."""
import base64
import json
from typing import Any

from app.platform.errors import invalid

DEFAULT_LIMIT, MAX_LIMIT = 25, 100


def clamp_limit(limit: int | None, maximum: int = MAX_LIMIT) -> int:
    if limit is None:
        return min(DEFAULT_LIMIT, maximum)
    if not 1 <= limit <= maximum:
        raise invalid(f"limit must be between 1 and {maximum}.", {"limit": f"1 to {maximum}."})
    return limit


def encode_cursor(values: list[Any]) -> str:
    return base64.urlsafe_b64encode(json.dumps(values, default=str).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None, size: int) -> list[Any] | None:
    if not cursor:
        return None
    try:
        values = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
    except (ValueError, UnicodeDecodeError) as exc:
        raise invalid("The cursor is not valid. Start from the first page.", {"cursor": "Invalid."}) from exc
    if not isinstance(values, list) or len(values) != size:
        raise invalid("The cursor is not valid. Start from the first page.", {"cursor": "Invalid."})
    return values


def page(rows: list[dict], limit: int, key: Any) -> tuple[list[dict], str | None]:
    """`rows` was fetched with limit + 1; `key(row)` returns the sort values that continue after that row."""
    if len(rows) > limit:
        rows = rows[:limit]
        return rows, encode_cursor(key(rows[-1]))
    return rows, None
