"""Scheduled jobs per company time zone (TASK-006, TASK-017 retention).

One tick per minute walks every company (ems.worker_organizations()) in its own transaction and RLS context.
Daily jobs (leakage + rule triggers 01:00, HR report 23:30, retention 02:00) are emitted as outbox events with deterministic IDs, so a repeated or
delayed tick inside the window can never run them twice; their handlers do the work.
"""
import datetime as dt
import logging
import uuid

from sqlalchemy import Engine, text

from app.hr import service as hr
from app.platform import events
from app.platform.db import Db, transaction
from app.platform.timeutil import Calendar, utcnow
from app.room import service as room
from app.room.livekit import MediaConfig
from worker.registry import Event, handles

log = logging.getLogger("ems.worker.jobs")
NS = uuid.UUID("2b7c0a3e-0d1f-4a8e-9a4b-6c1e5f0d7a21")          # namespace for deterministic scheduled-event IDs
VIEW_TOKEN_LIFETIME = dt.timedelta(minutes=15)                    # API-026 view token TTL
HR_REPORT_AT, RETENTION_AT, NIGHTLY_AT = dt.time(23, 30), dt.time(2, 0), dt.time(1, 0)
RETENTION = {                                                     # Section 32
    "presence_segments": ("ended_at", "12 months"), "stream_views": ("started_at", "12 months"),
    "agent_logs": ("created_at", "90 days"), "crawl_log": ("fetched_at", "90 days"),
    "notifications": ("created_at", "90 days"), "audit_events": ("occurred_at", "24 months"),
}


def scheduled_id(org_id: uuid.UUID, name: str, key: str) -> uuid.UUID:
    return uuid.uuid5(NS, f"{org_id}:{name}:{key}")


# ------------------------------------------------------------------------------------------------ every minute
def presence_timeouts(db: Db, now: dt.datetime) -> int:
    changed = 0
    for s in db.all(f"SELECT {room.SESSION_COLUMNS} FROM ems.work_sessions WHERE state = 'open' AND presence <> 'offline' "  # noqa: S608
                    "AND coalesce(last_heartbeat_at, started_at) < :t FOR UPDATE SKIP LOCKED", t=now - room.OFFLINE_AFTER):
        if room.mark_offline_if_silent(db, s, now):
            events.emit(db, s["org_id"], "room.presence_changed", {"user_id": str(s["user_id"]), "session_id": str(s["id"]), "to": "offline"})
            changed += 1
    return changed


def auto_close_sessions(db: Db, cal: Calendar, now: dt.datetime) -> int:
    """Open 2 hours after work end -> auto_closed at the last heartbeat (Section 31.1)."""
    closed = 0
    for s in db.all(f"SELECT {room.SESSION_COLUMNS} FROM ems.work_sessions WHERE state = 'open' FOR UPDATE SKIP LOCKED"):  # noqa: S608
        if now >= room.auto_close_deadline(cal, s):
            room.close_session(db, s, s["last_heartbeat_at"] or s["started_at"], "auto_closed")
            events.emit(db, s["org_id"], "room.checked_out", {"user_id": str(s["user_id"]), "session_id": str(s["id"]), "auto_closed": True})
            closed += 1
    return closed


def sweep_views(db: Db, media: MediaConfig) -> int:
    """Disconnect views that must end (token lifetime passed, live view switched off, the employee stopped sharing, the
    viewer deactivated) and retry removals that failed in the API. `ended_at` is written only after LiveKit removed
    the viewer (API-027), so a view stays open - and is retried next minute - while the media server is unreachable."""
    return len(room.disconnect_views(db, media, room.views_to_disconnect(db, VIEW_TOKEN_LIFETIME)))


# ------------------------------------------------------------------------------------------------ hourly
def emit_overdue_tasks(db: Db, org_id: uuid.UUID, now: dt.datetime) -> int:
    """task.overdue for each overdue open task, once per task, due date and day overdue (input for TASK-013 rules)."""
    n = 0
    for t in db.all("SELECT t.id, t.title, t.project_id, t.due_at, t.billable, p.billing_type, p.owner_id FROM ems.tasks t "
                    "JOIN ems.projects p ON p.id = t.project_id WHERE t.status <> 'done' AND t.due_at < :now", now=now):
        hours = int((now - t["due_at"]).total_seconds() // 3600)
        key = f"{t['id']}:{t['due_at'].isoformat()}:{hours // 24}"
        events.emit(db, org_id, "task.overdue", {"task_id": str(t["id"]), "project_id": str(t["project_id"]),
                                                 "project_owner_id": str(t["owner_id"]), "task.title": t["title"],
                                                 "task.hours_overdue": hours, "task.status": "overdue", "task.billable": t["billable"],
                                                 "project.billing_type": t["billing_type"]},
                    event_id=scheduled_id(org_id, "task.overdue", key))
        n += 1
    return n


# ------------------------------------------------------------------------------------------------ daily (via outbox)
@handles("platform.hr_daily_report")
def hr_daily_report(db: Db, e: Event) -> None:
    """The HR Agent 'reports to the CEO' through the daily report (Section 11): a summary notification for leaders."""
    org = db.one("SELECT time_zone, work_hours FROM ems.organizations")
    cal, day, now = Calendar(org["time_zone"], org["work_hours"]), dt.date.fromisoformat(e.payload["date"]), utcnow()
    members = [r["user_id"] for r in db.all("SELECT user_id FROM ems.memberships WHERE status = 'active'")]
    summaries, leave = hr.day_summaries(db, cal, members, day, now), hr.approved_leave_on(db, day)
    counts = {"present": 0, "on_leave": 0, "absent_unexplained": 0, "not_checked_in": 0}
    for u in members:
        status = hr.day_status(cal, day, day, now, u in summaries, u in leave)
        if status:
            counts[status] += 1
    late = sum(1 for s in summaries.values() if s["minutes_late"] > 0)
    leaders = [r["user_id"] for r in db.all("SELECT user_id FROM ems.memberships WHERE status = 'active' AND role IN ('ceo','coo','hr')")]
    events.notify(db, e.org_id, leaders, "hr.daily_report",
                  f"Daily report {day.isoformat()}: {counts['present']} present, {late} late, {counts['on_leave']} on leave, "
                  f"{counts['absent_unexplained']} absent", "hr_report", None)


@handles("platform.retention")
def retention(db: Db, e: Event) -> None:
    for table, (column, keep) in RETENTION.items():
        db.execute(f"DELETE FROM ems.{table} WHERE {column} < now() - CAST(:keep AS interval)", keep=keep)  # noqa: S608 - fixed names


def _in_window(local: dt.datetime, at: dt.time, minutes: int = 30) -> bool:
    start = local.replace(hour=at.hour, minute=at.minute, second=0, microsecond=0)
    return start <= local < start + dt.timedelta(minutes=minutes)


def tick(engine: Engine, media: MediaConfig | None = None) -> None:
    now, media = utcnow(), media or MediaConfig.from_env()
    with engine.connect() as conn:
        orgs = conn.execute(text("SELECT org_id, time_zone, work_hours FROM ems.worker_organizations()")).mappings().all()
    for org in orgs:
        try:
            with transaction(engine) as db:
                db.set_context(org["org_id"], None)
                cal = Calendar(org["time_zone"], org["work_hours"])
                local = cal.local(now)
                presence_timeouts(db, now)
                auto_close_sessions(db, cal, now)
                sweep_views(db, media)
                if local.minute == 0:
                    emit_overdue_tasks(db, org["org_id"], now)
                if _in_window(local, HR_REPORT_AT):
                    events.emit(db, org["org_id"], "platform.hr_daily_report", {"date": local.date().isoformat()},
                                event_id=scheduled_id(org["org_id"], "hr_daily_report", local.date().isoformat()))
                if _in_window(local, NIGHTLY_AT):                   # leakage run + nightly rule triggers (worker/automation.py)
                    events.emit(db, org["org_id"], "platform.nightly", {"date": local.date().isoformat()},
                                event_id=scheduled_id(org["org_id"], "nightly", local.date().isoformat()))
                if _in_window(local, RETENTION_AT):
                    events.emit(db, org["org_id"], "platform.retention", {"date": local.date().isoformat()},
                                event_id=scheduled_id(org["org_id"], "retention", local.date().isoformat()))
        except Exception:
            log.exception("scheduled tick failed", extra={"fields": {"org_id": str(org["org_id"])}})
