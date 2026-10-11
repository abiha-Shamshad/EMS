"""Audit rows, outbox events and in-app notifications, always written in the caller's transaction (spec Sections 31.2, 32).

Audit rows record actor, action, record and changed field *names* - never values.
"""
import uuid
from collections.abc import Iterable
from typing import Any

from app.platform.db import Db, jsonb


def audit(db: Db, org_id: Any, actor_id: Any, action: str, record_type: str | None = None, record_id: Any = None,
          changed_fields: Iterable[str] | None = None, request_id: str | None = None) -> None:
    db.execute(
        "INSERT INTO ems.audit_events (org_id, actor_id, action, record_type, record_id, changed_fields, request_id) "
        "VALUES (:org, :actor, :action, :rtype, :rid, :fields, :req)",
        org=org_id, actor=actor_id, action=action, rtype=record_type, rid=record_id,
        fields=sorted(changed_fields) if changed_fields is not None else None, req=request_id or None)


def emit(db: Db, org_id: Any, routing_key: str, payload: dict[str, Any], event_id: uuid.UUID | None = None) -> uuid.UUID:
    """Write a domain event to the outbox. A deterministic `event_id` makes scheduled emitters replay-safe."""
    eid = event_id or uuid.uuid4()
    db.execute(
        "INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (:id, :org, :key, CAST(:payload AS jsonb)) "
        "ON CONFLICT (id) DO NOTHING",
        id=eid, org=org_id, key=routing_key, payload=jsonb(payload))
    return eid


def notify(db: Db, org_id: Any, user_ids: Iterable[Any], kind: str, title: str,
           ref_type: str | None = None, ref_id: Any = None) -> int:
    count = 0
    for user_id in dict.fromkeys(u for u in user_ids if u):        # de-duplicate, keep order
        db.execute(
            "INSERT INTO ems.notifications (id, org_id, user_id, kind, title, ref_type, ref_id) "
            "VALUES (:id, :org, :usr, :kind, :title, :rtype, :rid)",
            id=uuid.uuid4(), org=org_id, usr=user_id, kind=kind, title=title[:300], rtype=ref_type, rid=ref_id)
        count += 1
    return count
