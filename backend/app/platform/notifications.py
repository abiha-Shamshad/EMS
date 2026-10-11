"""In-app notifications (API-069/070). Email copies need INT-003 and are not sent in Release 1."""
import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.platform.context import SessionCtx
from app.platform.errors import not_found
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok

router = APIRouter(prefix="/api/v1/notifications")


# ------------------------------------------------------------------------------------------------ API-069
@router.get("")
def list_notifications(ctx: SessionCtx, unread_only: bool = False, cursor: str | None = None,
                       limit: Annotated[int | None, Query()] = None):
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT id, kind, title, ref_type, ref_id, read_at, created_at FROM ems.notifications WHERE user_id = :me "
        "AND (NOT :unread OR read_at IS NULL) "
        "AND (CAST(:a_t AS timestamptz) IS NULL OR (created_at, id) < (CAST(:a_t AS timestamptz), CAST(:a_id AS uuid))) "
        "ORDER BY created_at DESC, id DESC LIMIT :lim",
        me=ctx.user_id, unread=unread_only, a_t=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["created_at"].isoformat(), str(r["id"])])
    unread = ctx.db.scalar("SELECT count(*) FROM ems.notifications WHERE user_id = :me AND read_at IS NULL", me=ctx.user_id)
    return ok({"items": [{"id": r["id"], "kind": r["kind"], "title": r["title"], "ref_type": r["ref_type"], "ref_id": r["ref_id"],
                          "read": r["read_at"] is not None, "created_at": r["created_at"]} for r in rows],
               "unread": unread, "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-070
@router.post("/{notification_id}/read")
def mark_read(notification_id: uuid.UUID, ctx: SessionCtx):
    found = ctx.db.scalar("UPDATE ems.notifications SET read_at = coalesce(read_at, now()) WHERE id = :n AND user_id = :me RETURNING id",
                          n=notification_id, me=ctx.user_id)
    if found is None:
        raise not_found("Notification")
    return ok({"id": notification_id, "read": True})
