"""Database access. The API connects as ems_app and the worker as ems_worker: never as ems_owner, which bypasses RLS.

Queries are explicit SQL (`text()`), executed through `Db`, a thin wrapper over one SQLAlchemy connection inside one
transaction. Bind values always go through parameters; identifiers are never built from user input.
Note: write casts as CAST(:x AS type) - SQLAlchemy does not treat ':x::type' as a bind parameter.
"""
import json
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.engine import CursorResult


class Db:
    def __init__(self, conn: Connection):
        self.conn = conn

    def execute(self, sql: str, **params: Any) -> CursorResult:
        return self.conn.execute(text(sql), params)

    def one(self, sql: str, **params: Any) -> dict[str, Any] | None:
        row = self.execute(sql, **params).mappings().first()
        return dict(row) if row is not None else None

    def all(self, sql: str, **params: Any) -> list[dict[str, Any]]:
        return [dict(r) for r in self.execute(sql, **params).mappings().all()]

    def scalar(self, sql: str, **params: Any) -> Any:
        return self.execute(sql, **params).scalar()

    @contextmanager
    def savepoint(self) -> Iterator[None]:
        """Run a statement that may hit a unique constraint without aborting the surrounding transaction."""
        nested = self.conn.begin_nested()
        try:
            yield
        except Exception:
            nested.rollback()
            raise
        else:
            nested.commit()

    def set_context(self, org_id: Any, user_id: Any) -> None:
        """Section 7.1 step 4: transaction-local tenant context (SET LOCAL cannot take bind parameters)."""
        self.execute("SELECT set_config('app.org_id', :org, true), set_config('app.user_id', :usr, true)",
                     org=str(org_id) if org_id else "", usr=str(user_id) if user_id else "")


def like_pattern(text_value: str) -> str:
    """'%<text>%' with LIKE wildcards in the user's text escaped (backslash is PostgreSQL's default LIKE escape)."""
    escaped = text_value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def jsonb(value: Any) -> str:
    """Serialize a value for a CAST(:param AS jsonb) placeholder."""
    return json.dumps(value, separators=(",", ":"), default=str)


def make_engine(url: str) -> Engine:
    return create_engine(url, pool_pre_ping=True, pool_size=10, max_overflow=10)


@contextmanager
def transaction(engine: Engine) -> Iterator[Db]:
    """One transaction on its own connection; commits on success, rolls back on any exception."""
    with engine.connect() as conn:
        with conn.begin():
            yield Db(conn)
