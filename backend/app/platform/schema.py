"""Request-body building blocks. Bodies reject unknown fields; money is a decimal string (DEC-011), never a float."""
import re
from decimal import Decimal, InvalidOperation
from typing import Annotated

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

_EMAIL = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$")
_MONEY = re.compile(r"^\d{1,12}(\.\d{1,2})?$")
_DOMAIN = re.compile(r"^(?=.{4,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


class Body(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not _EMAIL.match(value):
        raise ValueError("Enter a valid email address.")
    return value


def _money(value: object) -> Decimal:
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("Send amounts as decimal strings, for example \"5000.00\".")
    text = str(value).strip()
    if not _MONEY.match(text):
        raise ValueError("Use a decimal amount with at most 2 decimal places.")
    try:
        return Decimal(text)
    except InvalidOperation as exc:
        raise ValueError("Use a decimal amount.") from exc


def normalize_domain(value: str) -> str:
    """Accept 'https://www.Example.com/about' or 'example.com'; return 'example.com'."""
    v = value.strip().lower()
    v = re.sub(r"^[a-z]+://", "", v).split("/", 1)[0].split("?", 1)[0].split(":", 1)[0].rstrip(".")
    if v.startswith("www."):
        v = v[4:]
    return v


def is_valid_domain(value: str) -> bool:
    return bool(_DOMAIN.match(value))


def _domain(value: str) -> str:
    v = normalize_domain(value)
    if not is_valid_domain(v):
        raise ValueError("Enter a valid domain, for example example.com.")
    return v


Email = Annotated[str, AfterValidator(validate_email)]
Money = Annotated[Decimal, BeforeValidator(_money)]
Domain = Annotated[str, AfterValidator(_domain)]
Currency = Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
ExpectedVersion = Annotated[int, Field(ge=0)]
