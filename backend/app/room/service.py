"""Employee Room domain logic shared by the API, member deactivation and the worker (spec Sections 9.2-9.3).

Presence model (engine/presence.py): work_sessions holds the *current* presence and task; presence_segments holds
closed intervals. A segment is written only when presence or task changes. A heartbeat gap longer than OFFLINE_AFTER
becomes 'offline' starting HEARTBEAT_SECONDS after the last heartbeat - the same rule as engine.presence.segments().
"""
import datetime as dt
import logging
import uuid
from typing import Any

from app.engine import presence as presence_engine
from app.platform.db import Db
from app.platform.timeutil import Calendar
from app.room import livekit

log = logging.getLogger("ems.room")

OFFLINE_AFTER = dt.timedelta(seconds=presence_engine.OFFLINE_AFTER)
HEARTBEAT = dt.timedelta(seconds=presence_engine.HEARTBEAT_SECONDS)
SESSION_COLUMNS = "id, org_id, user_id, started_at, ended_at, state, current_task_id, last_heartbeat_at, presence, streaming"
CONSENT_COVERS = ["presence", "idle_state", "current_task", "live_screen_while_checked_in"]
CONSENT_EXCLUDES = ["recording", "keystrokes", "browsing_history", "webcam", "microphone"]


def open_session(db: Db, user_id: uuid.UUID, lock: bool = False) -> dict[str, Any] | None:
    return db.one(f"SELECT {SESSION_COLUMNS} FROM ems.work_sessions WHERE user_id = :u AND state = 'open'"  # noqa: S608
                  + (" FOR UPDATE" if lock else ""), u=user_id)


def session_by_id(db: Db, session_id: uuid.UUID, lock: bool = False) -> dict[str, Any] | None:
    return db.one(f"SELECT {SESSION_COLUMNS} FROM ems.work_sessions WHERE id = :s"  # noqa: S608
                  + (" FOR UPDATE" if lock else ""), s=session_id)


def has_current_consent(db: Db, user_id: uuid.UUID, policy_version: int) -> bool:
    return bool(db.scalar("SELECT 1 FROM ems.stream_consents WHERE user_id = :u AND policy_version = :v AND revoked_at IS NULL",
                          u=user_id, v=policy_version))


def streaming_allowed(db: Db, org: dict, user_id: uuid.UUID) -> bool:
    """Live view enabled for the company (OD-02) and the employee consented to the current notice (API-017)."""
    return bool(org["live_view_enabled"]) and has_current_consent(db, user_id, org["room_policy_version"])


def active_break(db: Db, user_id: uuid.UUID) -> dict[str, Any] | None:
    return db.one("SELECT id, session_id, kind, status, requested_minutes, started_at FROM ems.breaks "
                  "WHERE user_id = :u AND status = 'active'", u=user_id)


def presence_since(db: Db, session: dict) -> dt.datetime:
    last_end = db.scalar("SELECT max(ended_at) FROM ems.presence_segments WHERE session_id = :s", s=session["id"])
    return last_end or session["started_at"]


def _write_segment(db: Db, session: dict, presence: str, task_id: Any, start: dt.datetime, end: dt.datetime) -> None:
    if end > start:
        db.execute("INSERT INTO ems.presence_segments (id, org_id, session_id, user_id, presence, task_id, started_at, ended_at) "
                   "VALUES (:id, :org, :sid, :uid, :p, :t, :s, :e)",
                   id=uuid.uuid4(), org=session["org_id"], sid=session["id"], uid=session["user_id"], p=presence, t=task_id,
                   s=start, e=end)


def change_presence(db: Db, session: dict, new_presence: str, new_task_id: Any, at: dt.datetime) -> bool:
    """Close the running interval at `at` and switch to the new presence/task. Mutates `session`. Returns True on change."""
    if session["presence"] == new_presence and session["current_task_id"] == new_task_id:
        return False
    since = presence_since(db, session)
    at = max(at, since)
    _write_segment(db, session, session["presence"], session["current_task_id"], since, at)
    db.execute("UPDATE ems.work_sessions SET presence = :p, current_task_id = :t WHERE id = :s",
               p=new_presence, t=new_task_id, s=session["id"])
    session["presence"], session["current_task_id"] = new_presence, new_task_id
    return True


def mark_offline_if_silent(db: Db, session: dict, now: dt.datetime) -> bool:
    """No heartbeat for 90 s -> offline, starting 30 s after the last heartbeat (PRS-01/02)."""
    last = session["last_heartbeat_at"] or session["started_at"]
    if session["presence"] == "offline" or now - last <= OFFLINE_AFTER:
        return False
    return change_presence(db, session, "offline", session["current_task_id"], last + HEARTBEAT)


def segments_of(db: Db, session_ids: list[uuid.UUID]) -> list[dict[str, Any]]:
    if not session_ids:
        return []
    return db.all("SELECT session_id, presence, task_id, started_at, ended_at FROM ems.presence_segments "
                  "WHERE session_id = ANY(:ids) ORDER BY started_at", ids=session_ids)


def live_segments(db: Db, session: dict, now: dt.datetime) -> list[dict[str, Any]]:
    """Closed segments plus the running interval up to `now` (for totals of a session that is still open)."""
    segs = segments_of(db, [session["id"]])
    if session["state"] == "open":
        since = max([s["ended_at"] for s in segs], default=session["started_at"])
        if now > since:
            segs.append({"session_id": session["id"], "presence": session["presence"], "task_id": session["current_task_id"],
                         "started_at": since, "ended_at": now})
    return segs


def totals(segs: list[dict[str, Any]]) -> dict[str, int]:
    """Whole minutes per presence state (engine.presence.totals), with every state present."""
    t = presence_engine.totals([{"presence": s["presence"], "start": s["started_at"], "end": s["ended_at"]} for s in segs])
    return {k: t.get(k, 0) for k in ("active", "idle", "locked", "on_break", "offline")}


def _room_time_entries(db: Db, session: dict, segs: list[dict[str, Any]]) -> int:
    """Active minutes per selected task become one `room` time entry per task (Section 9.3, 12)."""
    by_task: dict[uuid.UUID, dict[str, Any]] = {}
    for s in segs:
        if s["presence"] == "active" and s["task_id"]:
            acc = by_task.setdefault(s["task_id"], {"seconds": 0.0, "start": s["started_at"]})
            acc["seconds"] += (s["ended_at"] - s["started_at"]).total_seconds()
            acc["start"] = min(acc["start"], s["started_at"])
    created = 0
    for task_id, acc in by_task.items():
        minutes = min(int(acc["seconds"] // 60), 1440)
        task = db.one("SELECT billable FROM ems.tasks WHERE id = :t", t=task_id)
        if minutes < 1 or task is None:
            continue
        db.execute("INSERT INTO ems.time_entries (id, org_id, task_id, user_id, started_at, minutes, source, billable) "
                   "VALUES (:id, :org, :t, :u, :s, :m, 'room', :b)",
                   id=uuid.uuid4(), org=session["org_id"], t=task_id, u=session["user_id"], s=acc["start"], m=minutes,
                   b=task["billable"])
        created += 1
    return created


def close_session(db: Db, session: dict, end_at: dt.datetime, state: str = "closed") -> dict[str, Any]:
    """Check-out, auto-close and deactivation: end any break, write the last segment, revoke the extension token,
    create Room time entries. Returns {"totals_minutes", "time_entries_created", "ended_at"}."""
    mark_offline_if_silent(db, session, end_at)          # a silent gap before check-out is offline time, not active time
    since = presence_since(db, session)
    end_at = max(end_at, since, session["started_at"] + dt.timedelta(seconds=1))
    _write_segment(db, session, session["presence"], session["current_task_id"], since, end_at)
    db.execute("UPDATE ems.breaks SET status = 'ended', ended_at = :e WHERE session_id = :s AND status = 'active'",
               e=end_at, s=session["id"])
    db.execute("UPDATE ems.breaks SET status = 'rejected' WHERE session_id = :s AND status = 'requested'", s=session["id"])
    db.execute("UPDATE ems.work_sessions SET state = :st, ended_at = :e, streaming = false WHERE id = :s",
               st=state, e=end_at, s=session["id"])
    db.execute("UPDATE ems.extension_tokens SET revoked_at = now() WHERE session_id = :s AND revoked_at IS NULL", s=session["id"])
    segs = segments_of(db, [session["id"]])
    return {"totals_minutes": totals(segs), "time_entries_created": _room_time_entries(db, session, segs), "ended_at": end_at}


# ------------------------------------------------------------------------------------------------ live views
VIEW_COLUMNS = "v.id, v.org_id, v.viewer_id, v.subject_user_id, v.started_at"


def open_views_involving(db: Db, user_id: uuid.UUID, as_viewer: bool = True) -> list[dict[str, Any]]:
    """Open views where the person is the employee being watched, or (with `as_viewer`) the viewer."""
    return db.all(f"SELECT {VIEW_COLUMNS} FROM ems.stream_views v WHERE v.ended_at IS NULL "  # noqa: S608 - constant columns
                  "AND (v.subject_user_id = :u OR (:viewer AND v.viewer_id = :u))", u=user_id, viewer=as_viewer)


def views_to_disconnect(db: Db, token_lifetime: dt.timedelta) -> list[dict[str, Any]]:
    """Open views that must end: past the view token lifetime, live view switched off for the company, the viewer
    deactivated, or the employee no longer sharing (checked out, on a break, consent withdrawn, offline).
    Runs under one company's RLS context."""
    return db.all(
        f"SELECT {VIEW_COLUMNS} FROM ems.stream_views v JOIN ems.organizations o ON o.id = v.org_id "  # noqa: S608 - constant columns
        "LEFT JOIN ems.work_sessions s ON s.user_id = v.subject_user_id AND s.state = 'open' "
        "JOIN ems.memberships viewer ON viewer.user_id = v.viewer_id "
        "WHERE v.ended_at IS NULL AND (v.started_at < now() - :life OR NOT o.live_view_enabled OR viewer.status <> 'active' "
        "OR s.id IS NULL OR NOT s.streaming OR s.presence IN ('on_break', 'offline') "
        "OR NOT EXISTS (SELECT 1 FROM ems.stream_consents c WHERE c.user_id = v.subject_user_id "
        "               AND c.policy_version = o.room_policy_version AND c.revoked_at IS NULL)) "
        "ORDER BY v.started_at", life=token_lifetime)


def disconnect_views(db: Db, media: livekit.MediaConfig, views: list[dict[str, Any]]) -> list[uuid.UUID]:
    """Remove each viewer from LiveKit, and record `ended_at` only once the removal succeeded. A view whose removal
    failed stays open; the every-minute worker sweep retries it. Returns the IDs of the views that ended."""
    ended = []
    for v in views:
        try:
            livekit.remove_viewer(media, v["org_id"], v["subject_user_id"], v["id"])
        except livekit.MediaError:
            log.warning("viewer removal failed; the sweep will retry", exc_info=True, extra={"fields": {"view_id": str(v["id"])}})
            continue
        if db.scalar("UPDATE ems.stream_views SET ended_at = now() WHERE id = :v AND ended_at IS NULL RETURNING id", v=v["id"]):
            ended.append(v["id"])
    return ended


def extension_token_expiry(calendar: Calendar, now: dt.datetime) -> dt.datetime:
    """Valid until 2 hours after the company's work end today, at most 14 hours (Section 7.3). Never less than 2 hours,
    so a late check-in (19:30 with work ending at 18:00) can still be closed from the extension."""
    candidate = max(calendar.work_end(calendar.local_date(now)) + dt.timedelta(hours=2), now + dt.timedelta(hours=2))
    return min(candidate, now + dt.timedelta(hours=14))


def auto_close_deadline(calendar: Calendar, session: dict) -> dt.datetime:
    """Sessions still open 2 hours after the work end of the day they started are auto-closed (Section 31.1)."""
    day = calendar.local_date(session["started_at"])
    deadline = calendar.work_end(day) + dt.timedelta(hours=2)
    return max(deadline, session["started_at"] + dt.timedelta(hours=2))


def break_minutes_used_today(db: Db, calendar: Calendar, user_id: uuid.UUID, now: dt.datetime) -> int:
    """Breaks started today: ended ones by actual length, the active one by its requested minutes."""
    start, end = calendar.day_bounds(calendar.local_date(now))
    return int(db.scalar(
        "SELECT coalesce(sum(CASE WHEN status = 'ended' THEN floor(extract(epoch FROM ended_at - started_at) / 60) "
        "ELSE requested_minutes END), 0) FROM ems.breaks "
        "WHERE user_id = :u AND status IN ('active','ended') AND started_at >= :s AND started_at < :e",
        u=user_id, s=start, e=end))
