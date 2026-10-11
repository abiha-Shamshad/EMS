"""JSON conventions (spec Section 19.2): UTC timestamps with Z, dates as YYYY-MM-DD, money as decimal strings."""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

TWO_PLACES = Decimal("0.01")


def money(value: Decimal | int | str | None) -> str | None:
    if value is None:
        return None
    return str(Decimal(value).quantize(TWO_PLACES))


def iso(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("naive datetime cannot be serialized; store and pass aware UTC datetimes")
    return value.astimezone(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def to_json(value: Any) -> Any:
    """Convert a response payload into JSON-safe values. Decimals must already be formatted with `money()`
    where they are amounts; any remaining Decimal is rendered as a plain string."""
    if isinstance(value, dict):
        return {str(k): to_json(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [to_json(v) for v in value]
    if isinstance(value, dt.datetime):
        return iso(value)
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value
