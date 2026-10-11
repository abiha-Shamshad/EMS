"""Outbox event handler registry (spec Section 31.2).

Handlers run inside the worker transaction that marks the event published, with the event's organization set as the
RLS context. Every handler for an event commits together with `published_at`, so a handler runs once per event
unless it raises (then the whole event is retried). Handlers must still be idempotent by event ID.

Other tasks register their own handlers here (for example the rule engine for `room.checked_in`, TASK-013).
"""
import datetime as dt
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.platform.db import Db


@dataclass(frozen=True)
class Event:
    id: uuid.UUID
    org_id: uuid.UUID
    routing_key: str
    payload: dict[str, Any]
    created_at: dt.datetime


Handler = Callable[[Db, Event], None]
HANDLERS: dict[str, list[Handler]] = {}


def handles(*routing_keys: str) -> Callable[[Handler], Handler]:
    def deco(fn: Handler) -> Handler:
        for key in routing_keys:
            HANDLERS.setdefault(key, []).append(fn)
        return fn
    return deco
