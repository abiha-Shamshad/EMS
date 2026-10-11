"""Idempotency-Key handling (spec Section 19.2) on creating POSTs marked "required".

The stored response is replayed for 24 hours; the same key with a different body returns 409 IDEMPOTENCY_KEY_REUSED.
The key row is inserted in the request transaction: a concurrent duplicate blocks on the primary key until the first
request commits (then replays its response) or rolls back (then runs itself). A failed request stores nothing, so a
retry recomputes the error.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from fastapi.responses import JSONResponse

from app.platform.context import Ctx
from app.platform.db import jsonb
from app.platform.errors import ApiError, invalid
from app.platform.responses import ok
from app.platform.security import sha256

HEADER = "Idempotency-Key"


@dataclass(frozen=True)
class IdempotencyKey:
    key: str
    route: str
    request_hash: bytes


async def idempotency_key(request: Request) -> IdempotencyKey:
    key = request.headers.get(HEADER, "")
    if not 8 <= len(key) <= 100:
        raise invalid("Send an Idempotency-Key header of 8 to 100 characters.", {HEADER: "8 to 100 characters."})
    raw = await request.body()
    try:
        canonical = json.dumps(json.loads(raw or b"{}"), sort_keys=True, separators=(",", ":"))
    except ValueError:
        canonical = raw.decode("utf-8", errors="replace")
    route = f"{request.method} {request.url.path}"
    return IdempotencyKey(key=key, route=route, request_hash=sha256(route + "\n" + canonical))


IdemKey = Annotated[IdempotencyKey, Depends(idempotency_key)]


def run_once(ctx: Ctx, idem: IdempotencyKey, handler: Callable[[], JSONResponse]) -> JSONResponse:
    db, ident = ctx.db, {"org": ctx.org_id, "actor": ctx.user_id, "route": idem.route, "key": idem.key}
    db.execute("DELETE FROM ems.idempotency_keys WHERE org_id = :org AND actor_id = :actor AND route = :route "
               "AND key = :key AND expires_at <= now()", **ident)
    inserted = db.scalar(
        "INSERT INTO ems.idempotency_keys (org_id, actor_id, route, key, request_hash, state, expires_at) "
        "VALUES (:org, :actor, :route, :key, :hash, 'in_progress', now() + interval '24 hours') "
        "ON CONFLICT DO NOTHING RETURNING 1", hash=idem.request_hash, **ident)
    if not inserted:
        row = db.one("SELECT request_hash, state, response_code, response_body FROM ems.idempotency_keys "
                     "WHERE org_id = :org AND actor_id = :actor AND route = :route AND key = :key", **ident)
        if row is None or bytes(row["request_hash"]) != idem.request_hash:
            raise ApiError("IDEMPOTENCY_KEY_REUSED", "This Idempotency-Key was already used for a different request.")
        if row["state"] != "completed":
            raise ApiError("IDEMPOTENCY_KEY_REUSED", "A request with this Idempotency-Key is still being processed.")
        stored = row["response_body"]
        return ok(stored.get("data"), stored.get("message"), status=row["response_code"])

    response = handler()
    body = json.loads(response.body)
    db.execute("UPDATE ems.idempotency_keys SET state = 'completed', response_code = :code, response_body = CAST(:body AS jsonb) "
               "WHERE org_id = :org AND actor_id = :actor AND route = :route AND key = :key",
               code=response.status_code, body=jsonb({"message": body.get("message"), "data": body.get("data")}), **ident)
    return response
