"""Live Employee Room (API-017..028): consent, check-in/out, heartbeats, breaks, screen-share tokens, live grid, views.

Trust rules (Section 9.1): nothing is captured silently; every view needs a reason and is shown to the employee;
live viewing stays off while organizations.live_view_enabled is false (OD-02).
"""
import datetime as dt
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import Field
from sqlalchemy.exc import IntegrityError

from app.platform import ratelimit
from app.platform.context import Ctx, EitherCtx, ExtensionCtx, SessionCtx
from app.platform.errors import ApiError, denied, invalid, not_found
from app.platform.pagination import clamp_limit, decode_cursor, encode_cursor
from app.platform.responses import ok
from app.platform.schema import Body
from app.platform.security import new_token
from app.platform.timeutil import utcnow
from app.room import livekit
from app.room import service as room

router = APIRouter(prefix="/api/v1/room")

HEARTBEAT_SECONDS = 30
LIVE_GRID_MAX = 48


def _first_name(name: str) -> str:
    return name.split(" ", 1)[0] if name else "This person"


def _require_task(ctx: Ctx, task_id: uuid.UUID | None) -> None:
    if task_id is not None and not ctx.db.scalar("SELECT 1 FROM ems.tasks WHERE id = :t", t=task_id):
        raise invalid("That task does not exist.", {"task_id": "Unknown task."})


def _own_open_session(ctx: Ctx, session_id: uuid.UUID | None, lock: bool = True) -> dict:
    """The caller's open session. An extension token is bound to the session it was issued for."""
    session = room.open_session(ctx.db, ctx.user_id, lock=lock)
    if session is None or (ctx.ext_session_id and session["id"] != ctx.ext_session_id):
        raise ApiError("NO_OPEN_SESSION", "You are not checked in.")
    if session_id is not None and session_id != session["id"]:
        raise ApiError("SESSION_CLOSED", "Your work session has ended. Check in again to continue.")
    return session


def _disconnect_viewers_of(ctx: Ctx, subject_id: uuid.UUID) -> None:
    """Sharing stopped (consent withdrawn, break started): drop everyone watching now. Failures are left to the sweep,
    so the employee's own action never fails because the media server is slow."""
    room.disconnect_views(ctx.db, livekit.MediaConfig.of(ctx.settings), room.open_views_involving(ctx.db, subject_id, as_viewer=False))


def _media_state(live_view_enabled: bool, presence: str, on: bool) -> str:
    """Grid state of one feed (screen or webcam): disabled (OD-02 switch off), paused (break), live or off."""
    if not live_view_enabled:
        return "disabled"
    if presence == "on_break":
        return "paused"
    return "live" if on and presence != "offline" else "off"


def _derived_presence(session: dict, now: dt.datetime) -> str:
    """Presence as of `now`, even if the every-minute offline sweep has not run yet (PRS-02)."""
    last = session["last_heartbeat_at"] or session["started_at"]
    if session["presence"] != "offline" and now - last > room.OFFLINE_AFTER:
        return "offline"
    return session["presence"]


# ------------------------------------------------------------------------------------------------ API-017
class ConsentIn(Body):
    policy_version: int = Field(ge=1)
    accept: bool
    webcam: bool = False                     # separate opt-in to the live webcam while checked in (db/006)


@router.post("/consent")
def consent(body: ConsentIn, ctx: SessionCtx):
    ctx.require("room.self")
    current = ctx.org["room_policy_version"]
    if body.policy_version < current:
        raise ApiError("POLICY_VERSION_OUTDATED", f"A newer monitoring notice exists. Read version {current} before accepting.",
                       {"current_version": current})
    if body.policy_version > current:
        raise invalid("That notice version does not exist.", {"policy_version": f"Current version is {current}."})
    if not body.accept:
        revoked_at = utcnow()
        ctx.db.execute("UPDATE ems.stream_consents SET revoked_at = :t WHERE user_id = :u AND revoked_at IS NULL",
                       t=revoked_at, u=ctx.user_id)
        ctx.db.execute("UPDATE ems.work_sessions SET streaming = false, camera = false WHERE user_id = :u AND state = 'open'", u=ctx.user_id)
        _disconnect_viewers_of(ctx, ctx.user_id)
        ctx.audit("room.consent_revoked", "stream_consent", ctx.user_id)
        ctx.emit("room.consent_changed", {"user_id": str(ctx.user_id), "accepted": False, "policy_version": current})
        return ok({"policy_version": current, "revoked_at": revoked_at, "stream_stopped": True},
                  "Consent withdrawn. Screen and webcam sharing have stopped.")
    consented_at = ctx.db.scalar(
        "INSERT INTO ems.stream_consents (org_id, user_id, policy_version, webcam) VALUES (:org, :u, :v, :w) "
        "ON CONFLICT (org_id, user_id, policy_version) DO UPDATE SET revoked_at = NULL, webcam = EXCLUDED.webcam, consented_at = "
        "CASE WHEN ems.stream_consents.revoked_at IS NULL THEN ems.stream_consents.consented_at ELSE now() END "
        "RETURNING consented_at", org=ctx.org_id, u=ctx.user_id, v=current, w=body.webcam)
    if not body.webcam:                                          # webcam opt-out keeps screen consent but stops the camera
        ctx.db.execute("UPDATE ems.work_sessions SET camera = false WHERE user_id = :u AND state = 'open'", u=ctx.user_id)
    ctx.audit("room.consent_given", "stream_consent", ctx.user_id, ["webcam"] if body.webcam else None)
    ctx.emit("room.consent_changed", {"user_id": str(ctx.user_id), "accepted": True, "webcam": body.webcam, "policy_version": current})
    covers, excludes = room.consent_scope(body.webcam)
    return ok({"policy_version": current, "consented_at": consented_at, "covers": covers, "excludes": excludes, "webcam": body.webcam},
              "Consent recorded.")


# ------------------------------------------------------------------------------------------------ API-018
class Device(Body):
    kind: Literal["chrome_extension", "web"]
    extension_version: str | None = Field(default=None, max_length=20)


class CheckInIn(Body):
    device: Device | None = None
    task_id: uuid.UUID | None = None


def _issue_extension_token(ctx: Ctx, session_id: uuid.UUID, now: dt.datetime) -> str:
    """Bearer token for the extension, bound to one work session (DB-17); only its hash is stored."""
    token, token_hash = new_token("ext")
    ctx.db.execute("INSERT INTO ems.extension_tokens (token_hash, org_id, user_id, session_id, expires_at) VALUES (:h, :org, :u, :s, :exp)",
                   h=token_hash, org=ctx.org_id, u=ctx.user_id, s=session_id, exp=room.extension_token_expiry(ctx.calendar, now))
    return token


@router.post("/check-in", status_code=201)
def check_in(body: CheckInIn, ctx: EitherCtx):
    ctx.require("room.self")
    db, cal, now = ctx.db, ctx.calendar, utcnow()
    existing = room.open_session(db, ctx.user_id, lock=True)
    if existing is not None:
        reply = {"session_id": existing["id"], "started_at": existing["started_at"], "presence": existing["presence"], "already_open": True}
        if body.device and body.device.kind == "chrome_extension" and ctx.via == "session":
            # Checked in on the web first: the extension attaches to that session with a fresh token (earlier ones revoked).
            db.execute("UPDATE ems.extension_tokens SET revoked_at = now() WHERE session_id = :s AND revoked_at IS NULL", s=existing["id"])
            token = _issue_extension_token(ctx, existing["id"], now)
            ctx.audit("room.extension_attached", "work_session", existing["id"])
            reply.update(extension_token=token, heartbeat_seconds=HEARTBEAT_SECONDS,
                         streaming_required=room.streaming_allowed(db, ctx.org, ctx.user_id),
                         camera_allowed=room.camera_allowed(db, ctx.org, ctx.user_id))
        return ok(reply)
    today = cal.local_date(now)
    if db.scalar("SELECT 1 FROM ems.leave_requests WHERE user_id = :u AND status = 'approved' AND period @> CAST(:d AS date)",
                 u=ctx.user_id, d=today):
        raise ApiError("ON_APPROVED_LEAVE", "You are on approved leave today. Ask HR to cancel the leave before checking in.")
    _require_task(ctx, body.task_id)

    session_id = uuid.uuid4()
    try:
        with db.savepoint():
            db.execute("INSERT INTO ems.work_sessions (id, org_id, user_id, started_at, current_task_id, last_heartbeat_at, presence) "
                       "VALUES (:id, :org, :u, :t, :task, :t, 'active')",
                       id=session_id, org=ctx.org_id, u=ctx.user_id, t=now, task=body.task_id)
    except IntegrityError:                               # concurrent check-in won the unique index (DB-06)
        existing = room.open_session(db, ctx.user_id)
        return ok({"session_id": existing["id"], "started_at": existing["started_at"], "presence": existing["presence"],
                   "already_open": True})

    token = _issue_extension_token(ctx, session_id, now)
    minutes_late = cal.minutes_late(now)
    streaming_required = room.streaming_allowed(db, ctx.org, ctx.user_id)
    ctx.audit("room.checked_in", "work_session", session_id)
    ctx.emit("room.checked_in", {"user_id": str(ctx.user_id), "session_id": str(session_id), "minutes_late": minutes_late})
    local = cal.local(now)
    return ok({"session_id": session_id, "started_at": now, "minutes_late": minutes_late, "presence": "active",
               "extension_token": token, "heartbeat_seconds": HEARTBEAT_SECONDS, "streaming_required": streaming_required,
               "camera_allowed": room.camera_allowed(db, ctx.org, ctx.user_id), "next": "start_screen_share" if streaming_required else "work"},
              f"Checked in at {local.strftime('%I:%M %p').lstrip('0')}.", status=201)


# ------------------------------------------------------------------------------------------------ API-019
class HeartbeatIn(Body):
    session_id: uuid.UUID
    sent_at: dt.datetime
    idle_state: Literal["active", "idle", "locked"]
    streaming: bool
    camera: bool = False                     # the extension is publishing the webcam
    task_id: uuid.UUID | None = None


@router.post("/heartbeat")
def heartbeat(body: HeartbeatIn, request: Request, ctx: ExtensionCtx):
    ratelimit.hit(request.app.state.engine, "heartbeat", str(ctx.ext_session_id))
    db, now = ctx.db, utcnow()
    session = room.session_by_id(db, ctx.ext_session_id, lock=True)
    if session is None or session["state"] != "open" or body.session_id != session["id"]:
        raise ApiError("SESSION_CLOSED", "Your work session has ended. Check in again to continue.")
    task_id = session["current_task_id"]
    if "task_id" in body.model_fields_set:
        _require_task(ctx, body.task_id)
        task_id = body.task_id

    room.mark_offline_if_silent(db, session, now)
    on_break = room.active_break(db, ctx.user_id) is not None
    previous = session["presence"]
    new_presence = "on_break" if on_break else body.idle_state
    if room.change_presence(db, session, new_presence, task_id, now) and previous != new_presence:
        ctx.emit("room.presence_changed", {"user_id": str(ctx.user_id), "session_id": str(session["id"]),
                                           "from": previous, "to": new_presence})
    # The extension's report is honoured only when sharing is allowed right now.
    streaming = body.streaming and not on_break and room.streaming_allowed(db, ctx.org, ctx.user_id)
    camera = body.camera and not on_break and room.camera_allowed(db, ctx.org, ctx.user_id)
    if streaming != session["streaming"] or camera != session["camera"]:
        ctx.emit("room.stream_state", {"user_id": str(ctx.user_id), "session_id": str(session["id"]), "streaming": streaming, "camera": camera})
    db.execute("UPDATE ems.work_sessions SET last_heartbeat_at = :t, streaming = :s, camera = :c WHERE id = :id",
               t=now, s=streaming, c=camera, id=session["id"])
    pending = db.one("SELECT id FROM ems.breaks WHERE session_id = :s AND status = 'requested' ORDER BY created_at DESC LIMIT 1",
                     s=session["id"])
    return ok({"presence": new_presence, "server_time": now, "next_heartbeat_seconds": HEARTBEAT_SECONDS,
               "pending_break_decision": {"break_id": pending["id"], "status": "requested"} if pending else None})


# ------------------------------------------------------------------------------------------------ API-020
class CheckOutIn(Body):
    session_id: uuid.UUID | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.post("/check-out")
def check_out(body: CheckOutIn, ctx: EitherCtx):
    ctx.require("room.self")
    db = ctx.db
    session = room.open_session(db, ctx.user_id, lock=True)
    if session is None or (body.session_id and session["id"] != body.session_id):
        closed = room.session_by_id(db, body.session_id) if body.session_id else None
        if closed and closed["user_id"] == ctx.user_id and closed["state"] != "open":     # repeat returns the closed session
            segs = room.segments_of(db, [closed["id"]])
            entries = db.scalar("SELECT count(*) FROM ems.time_entries WHERE user_id = :u AND source = 'room' "
                                "AND started_at >= :s AND started_at < :e", u=ctx.user_id, s=closed["started_at"], e=closed["ended_at"])
            return ok({"session_id": closed["id"], "started_at": closed["started_at"], "ended_at": closed["ended_at"],
                       "totals_minutes": room.totals(segs), "time_entries_created": entries})
        raise ApiError("NO_OPEN_SESSION", "You are not checked in.")
    if ctx.ext_session_id and session["id"] != ctx.ext_session_id:
        raise ApiError("NO_OPEN_SESSION", "You are not checked in.")

    result = room.close_session(db, session, utcnow(), "closed")
    if body.note:
        db.execute("INSERT INTO ems.activities (id, org_id, entity_type, entity_id, kind, note, actor_id, occurred_at) "
                   "VALUES (:id, :org, 'employee', :u, 'note', :n, :u, :t)",
                   id=uuid.uuid4(), org=ctx.org_id, u=ctx.user_id, n=body.note, t=result["ended_at"])
    ctx.audit("room.checked_out", "work_session", session["id"])
    ctx.emit("room.checked_out", {"user_id": str(ctx.user_id), "session_id": str(session["id"])})
    return ok({"session_id": session["id"], "started_at": session["started_at"], "ended_at": result["ended_at"],
               "totals_minutes": result["totals_minutes"], "time_entries_created": result["time_entries_created"]},
              "Checked out. Good work today.")


# ------------------------------------------------------------------------------------------------ API-021
class BreakIn(Body):
    session_id: uuid.UUID
    kind: Literal["short", "lunch", "prayer", "personal"]
    minutes: int = Field(ge=5, le=120)


@router.post("/breaks", status_code=201)
def request_break(body: BreakIn, ctx: EitherCtx):
    ctx.require("room.self")
    db, now = ctx.db, utcnow()
    session = _own_open_session(ctx, body.session_id)
    if db.scalar("SELECT 1 FROM ems.breaks WHERE user_id = :u AND status IN ('active','requested')", u=ctx.user_id):
        raise ApiError("BREAK_ALREADY_ACTIVE", "You already have an active break.")
    used = room.break_minutes_used_today(db, ctx.calendar, ctx.user_id, now)
    within = used + body.minutes <= ctx.org["daily_break_allowance_minutes"]
    break_id = uuid.uuid4()
    try:
        with db.savepoint():
            db.execute("INSERT INTO ems.breaks (id, org_id, session_id, user_id, kind, status, requested_minutes, started_at) "
                       "VALUES (:id, :org, :s, :u, :k, :st, :m, :t)",
                       id=break_id, org=ctx.org_id, s=session["id"], u=ctx.user_id, k=body.kind,
                       st="active" if within else "requested", m=body.minutes, t=now if within else None)
    except IntegrityError as exc:                        # ux_one_active_break
        raise ApiError("BREAK_ALREADY_ACTIVE", "You already have an active break.") from exc
    if within:
        room.change_presence(db, session, "on_break", session["current_task_id"], now)
        db.execute("UPDATE ems.work_sessions SET streaming = false, camera = false WHERE id = :s", s=session["id"])
        _disconnect_viewers_of(ctx, ctx.user_id)
    ctx.audit("room.break_requested", "break", break_id)
    ctx.emit("room.break_requested", {"user_id": str(ctx.user_id), "break_id": str(break_id), "kind": body.kind,
                                      "minutes": body.minutes, "needs_approval": not within})
    label = body.kind.capitalize()
    message = f"{label} break started. Screen sharing paused." if within else f"{label} break request sent for approval."
    return ok({"break_id": break_id, "status": "active" if within else "requested", "started_at": now if within else None,
               "approval": "auto_approved_by_policy" if within else "manager_required", "stream_paused": within},
              message, status=201)


# ------------------------------------------------------------------------------------------------ break list (web)
@router.get("/breaks")
def list_breaks(ctx: SessionCtx, status: Literal["requested", "active", "ended", "rejected"] | None = None,
                from_: Annotated[dt.date | None, Query(alias="from")] = None, to: Annotated[dt.date | None, Query()] = None):
    """Break requests to decide (API-022) and the break log. Read-only. People holding leave.decide see their scope
    (team or company); everyone else sees their own breaks."""
    cal = ctx.calendar
    to = to or cal.local_date()
    from_ = from_ or to - dt.timedelta(days=6)
    if from_ > to or (to - from_).days > 62:
        raise invalid("Choose a date range of at most 62 days.", {"from": "Must be on or before 'to'."})
    scope = ctx.scope("leave.decide")
    users = None if scope == "all" else [*ctx.team_ids(), ctx.user_id] if scope == "team" else [ctx.user_id]
    rows = ctx.db.all(
        "SELECT b.id, b.user_id, u.name, b.kind, b.status, b.requested_minutes, b.started_at, b.ended_at, b.created_at FROM ems.breaks b "
        "JOIN ems.users u ON u.id = b.user_id WHERE (CAST(:st AS text) IS NULL OR b.status = :st) "
        "AND (CAST(:users AS uuid[]) IS NULL OR b.user_id = ANY(CAST(:users AS uuid[]))) AND b.created_at >= :s AND b.created_at < :e "
        "ORDER BY b.created_at DESC LIMIT 500",
        st=status, users=users, s=cal.day_bounds(from_)[0], e=cal.day_bounds(to)[1])

    def minutes(r) -> int | None:
        return int((r["ended_at"] - r["started_at"]).total_seconds() // 60) if r["ended_at"] and r["started_at"] else None
    return ok({"items": [{**r, "minutes": minutes(r),
                          "can_decide": r["status"] == "requested" and r["user_id"] != ctx.user_id and ctx.covers("leave.decide", r["user_id"])}
                         for r in rows]})


# ------------------------------------------------------------------------------------------------ API-022
class BreakDecisionIn(Body):
    decision: Literal["approved", "rejected"]


@router.post("/breaks/{break_id}/decision")
def decide_break(break_id: uuid.UUID, body: BreakDecisionIn, ctx: SessionCtx):
    db, now = ctx.db, utcnow()
    brk = db.one("SELECT id, session_id, user_id, status FROM ems.breaks WHERE id = :b FOR UPDATE", b=break_id)
    if brk is None:
        raise not_found("Break")
    if brk["user_id"] == ctx.user_id or not ctx.covers("leave.decide", brk["user_id"]):
        raise denied("You cannot decide this break request.")
    if brk["status"] != "requested":
        raise ApiError("ALREADY_DECIDED", "This break request was already decided.")
    started_at = None
    if body.decision == "approved":
        session = room.session_by_id(db, brk["session_id"], lock=True)
        if session is None or session["state"] != "open":
            raise ApiError("SESSION_CLOSED", "The employee's work session has ended.")
        if room.active_break(db, brk["user_id"]):
            raise ApiError("BREAK_ALREADY_ACTIVE", "The employee already has an active break.")
        started_at = now
        db.execute("UPDATE ems.breaks SET status = 'active', started_at = :t, decided_by = :me WHERE id = :b",
                   t=now, me=ctx.user_id, b=break_id)
        room.change_presence(db, session, "on_break", session["current_task_id"], now)
        db.execute("UPDATE ems.work_sessions SET streaming = false, camera = false WHERE id = :s", s=session["id"])
        _disconnect_viewers_of(ctx, brk["user_id"])
    else:
        db.execute("UPDATE ems.breaks SET status = 'rejected', decided_by = :me WHERE id = :b", me=ctx.user_id, b=break_id)
    ctx.audit("room.break_decided", "break", break_id, ["status"])
    ctx.emit("room.break_decided", {"user_id": str(brk["user_id"]), "break_id": str(break_id), "decision": body.decision})
    return ok({"break_id": break_id, "status": "active" if started_at else "rejected", "started_at": started_at,
               "decided_by": ctx.user_id})


# ------------------------------------------------------------------------------------------------ API-023
@router.post("/breaks/{break_id}/end")
def end_break(break_id: uuid.UUID, ctx: EitherCtx):
    db, now = ctx.db, utcnow()
    brk = db.one("SELECT id, session_id, user_id, status, started_at, ended_at FROM ems.breaks WHERE id = :b FOR UPDATE", b=break_id)
    if brk is None or brk["user_id"] != ctx.user_id:
        raise not_found("Break")
    allowance = ctx.org["daily_break_allowance_minutes"]
    if brk["status"] == "active":
        db.execute("UPDATE ems.breaks SET status = 'ended', ended_at = :t WHERE id = :b", t=now, b=break_id)
        brk["ended_at"] = now
        session = room.session_by_id(db, brk["session_id"], lock=True)
        if session and session["state"] == "open" and session["presence"] == "on_break":
            room.change_presence(db, session, "active", session["current_task_id"], now)
        ctx.audit("room.break_ended", "break", break_id)
        ctx.emit("room.break_ended", {"user_id": str(ctx.user_id), "break_id": str(break_id)})
    elif brk["status"] != "ended":
        raise ApiError("INVALID_TRANSITION", "Only an active break can be ended.", {"from": brk["status"], "allowed": ["active"]})
    minutes = int((brk["ended_at"] - brk["started_at"]).total_seconds() // 60)
    used = room.break_minutes_used_today(db, ctx.calendar, ctx.user_id, brk["started_at"])
    over = min(max(0, used - allowance), minutes)
    return ok({"break_id": break_id, "status": "ended", "minutes": minutes, "over_allowance_minutes": over,
               "stream_resume": room.streaming_allowed(db, ctx.org, ctx.user_id)})


# ------------------------------------------------------------------------------------------------ API-024
class PublishTokenIn(Body):
    session_id: uuid.UUID
    camera: bool = False                     # also allow publishing the webcam (needs the webcam opt-in)


@router.post("/stream/publish-token")
def publish_token(body: PublishTokenIn, ctx: ExtensionCtx):
    db = ctx.db
    session = _own_open_session(ctx, body.session_id, lock=False)
    if not ctx.org["live_view_enabled"]:
        raise denied("Live screen viewing is switched off for this company.")
    if not room.has_current_consent(db, ctx.user_id, ctx.org["room_policy_version"]):
        raise ApiError("CONSENT_REQUIRED", "Accept the monitoring notice before sharing your screen.",
                       {"policy_version": ctx.org["room_policy_version"]})
    if body.camera and not room.has_webcam_consent(db, ctx.user_id, ctx.org["room_policy_version"]):
        raise ApiError("CONSENT_REQUIRED", "Opt in to the webcam in the monitoring notice before turning the camera on.",
                       {"policy_version": ctx.org["room_policy_version"], "webcam": True})
    if room.active_break(db, ctx.user_id):
        raise ApiError("ON_BREAK", "You are on a break. Sharing resumes when the break ends.")
    token = livekit.publish_token(ctx.settings, ctx.org_id, ctx.user_id, camera=body.camera)
    ctx.audit("room.stream_started", "work_session", session["id"])
    ctx.emit("room.stream_state", {"user_id": str(ctx.user_id), "session_id": str(session["id"]), "streaming": "token_issued"})
    return ok({"livekit_url": ctx.settings.livekit_url, "token": token, "room": livekit.room_name(ctx.org_id, ctx.user_id),
               "identity": f"employee:{ctx.user_id}",
               "grants": {"can_publish": True, "can_subscribe": False, "can_publish_data": False,
                          "can_publish_sources": livekit.publish_sources(body.camera)},
               "expires_in_seconds": livekit.PUBLISH_TTL_SECONDS, "video": {"max_resolution": "1280x720", "max_fps": 5}})


# ------------------------------------------------------------------------------------------------ API-025
@router.get("/live")
def live_grid(ctx: SessionCtx, department: str | None = None,
              presence: Literal["active", "idle", "locked", "on_break", "offline"] | None = None,
              cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    ctx.require("room.view_live", "Only the CEO and COO can open the live room.")
    db, cal, now = ctx.db, ctx.calendar, utcnow()
    limit = clamp_limit(limit, LIVE_GRID_MAX)
    rows = db.all(
        "SELECT s.id, s.org_id, s.user_id, s.started_at, s.ended_at, s.state, s.current_task_id, s.last_heartbeat_at, s.presence, "
        "s.streaming, s.camera, u.name, m.department, t.title AS task_title, "
        "(SELECT max(ended_at) FROM ems.presence_segments p WHERE p.session_id = s.id) AS last_change "
        "FROM ems.work_sessions s JOIN ems.memberships m ON m.user_id = s.user_id JOIN ems.users u ON u.id = s.user_id "
        "LEFT JOIN ems.tasks t ON t.id = s.current_task_id WHERE s.state = 'open' ORDER BY u.name, s.user_id")
    today = cal.local_date(now)
    counts = {"checked_in": len(rows), "active": 0, "idle": 0, "locked": 0, "on_break": 0, "offline": 0}
    items = []
    for r in rows:
        p = _derived_presence(r, now)
        counts[p] += 1
        if (department and r["department"] != department) or (presence and p != presence):
            continue
        since = r["last_change"] or r["started_at"]
        if p == "offline" and r["presence"] != "offline":
            since = (r["last_heartbeat_at"] or r["started_at"]) + room.HEARTBEAT
        enabled = ctx.org["live_view_enabled"]
        items.append({"user_id": r["user_id"], "name": r["name"], "department": r["department"], "presence": p, "since": since,
                      "current_task": {"id": r["current_task_id"], "title": r["task_title"]} if r["current_task_id"] else None,
                      "stream": _media_state(enabled, p, r["streaming"]), "camera": _media_state(enabled, p, r["camera"]),
                      "minutes_late": cal.minutes_late(r["started_at"])})
    on_leave = db.scalar("SELECT count(DISTINCT user_id) FROM ems.leave_requests WHERE status = 'approved' AND period @> CAST(:d AS date)",
                         d=today)
    start, end = cal.day_bounds(today)
    seen_today = db.scalar("SELECT count(DISTINCT user_id) FROM ems.work_sessions WHERE state = 'open' OR (started_at >= :s AND started_at < :e)",
                           s=start, e=end)
    headcount = db.scalar("SELECT count(*) FROM ems.memberships WHERE status = 'active'")
    counts["on_leave"] = on_leave
    counts["not_checked_in"] = max(0, headcount - seen_today - on_leave) if cal.is_working_day(today) else 0

    after = decode_cursor(cursor, 2)
    if after:
        items = [i for i in items if (i["name"], str(i["user_id"])) > (after[0], after[1])]
    next_cursor = encode_cursor([items[limit - 1]["name"], str(items[limit - 1]["user_id"])]) if len(items) > limit else None
    return ok({"as_of": now, "live_view_enabled": ctx.org["live_view_enabled"], "counts": counts, "items": items[:limit],
               "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-026
class ViewIn(Body):
    subject_user_id: uuid.UUID
    reason: str = Field(min_length=3, max_length=200)


@router.post("/stream/view", status_code=201)
def open_view(body: ViewIn, ctx: SessionCtx):
    ctx.require("room.view_live", "Only the CEO and COO can open the live room.")
    db, now = ctx.db, utcnow()
    if body.subject_user_id == ctx.user_id:
        raise invalid("You cannot open your own screen.", {"subject_user_id": "Choose someone else."})
    subject = db.one("SELECT m.status, u.name FROM ems.memberships m JOIN ems.users u ON u.id = m.user_id WHERE m.user_id = :u",
                     u=body.subject_user_id)
    if subject is None or subject["status"] != "active":
        raise not_found("Employee")
    if not ctx.org["live_view_enabled"]:
        raise denied("Live screen viewing is switched off for this company.")
    session = room.open_session(db, body.subject_user_id)
    state = _derived_presence(session, now) if session else "not_checked_in"
    if session is None or not (session["streaming"] or session["camera"]) or state in ("on_break", "offline"):
        raise ApiError("STREAM_NOT_LIVE", f"{_first_name(subject['name'])} is not live right now (on break, not sharing or not checked in).",
                       {"presence": state})
    viewer_name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=ctx.user_id)
    view = _start_view(ctx, body.subject_user_id, body.reason, viewer_name, now)
    return ok({**view, "livekit_url": ctx.settings.livekit_url, "grants": {"can_publish": False, "can_subscribe": True, "can_publish_data": False},
               "expires_in_seconds": livekit.VIEW_TTL_SECONDS, "subject_notified": True}, status=201)


def _start_view(ctx: Ctx, subject_id: uuid.UUID, reason: str, viewer_name: str, now: dt.datetime) -> dict:
    """One audited view of one employee: stream_views row, in-app notice, subscribe-only token for their room."""
    view_id = uuid.uuid4()
    token = livekit.view_token(ctx.settings, ctx.org_id, subject_id, view_id)
    ctx.db.execute("INSERT INTO ems.stream_views (id, org_id, viewer_id, subject_user_id, reason, started_at) VALUES (:id, :org, :v, :s, :r, :t)",
                   id=view_id, org=ctx.org_id, v=ctx.user_id, s=subject_id, r=reason, t=now)
    # Written in this transaction (not by the worker) so the employee is told about every view that exists (G5).
    ctx.notify([subject_id], "room.view_started", f"{viewer_name} is viewing you live: {reason}", "stream_view", view_id)
    ctx.audit("room.stream_viewed", "stream_view", view_id, ["viewer_id", "subject_user_id", "reason"])
    ctx.emit("room.view_started", {"view_id": str(view_id), "viewer_id": str(ctx.user_id), "subject_user_id": str(subject_id)})
    return {"view_id": view_id, "token": token, "room": livekit.room_name(ctx.org_id, subject_id)}


# ------------------------------------------------------------------------------------------------ video grid (web)
GRID_MAX = 48


class GridViewIn(Body):
    reason: str = Field(min_length=3, max_length=200)
    subject_user_ids: list[uuid.UUID] | None = Field(default=None, max_length=GRID_MAX)


@router.post("/stream/view-grid", status_code=201)
def open_grid(body: GridViewIn, ctx: SessionCtx):
    """CEO/COO video wall: one reason opens a view of everyone who is live right now (webcam and/or screen). Each person
    gets their own logged view, their own notice and a subscribe-only token for their own room, exactly as API-026."""
    ctx.require("room.view_live", "Only the CEO and COO can open the live room.")
    db, now = ctx.db, utcnow()
    if not ctx.org["live_view_enabled"]:
        raise denied("Live viewing is switched off for this company.")
    rows = db.all("SELECT s.user_id, s.presence, s.last_heartbeat_at, s.started_at, s.streaming, s.camera, u.name "
                  "FROM ems.work_sessions s JOIN ems.users u ON u.id = s.user_id JOIN ems.memberships m ON m.user_id = s.user_id "
                  "WHERE s.state = 'open' AND m.status = 'active' AND (s.streaming OR s.camera) AND s.user_id <> :me "
                  "AND (CAST(:ids AS uuid[]) IS NULL OR s.user_id = ANY(CAST(:ids AS uuid[]))) ORDER BY u.name LIMIT :lim",
                  me=ctx.user_id, ids=body.subject_user_ids, lim=GRID_MAX)
    viewer_name = db.scalar("SELECT name FROM ems.users WHERE id = :u", u=ctx.user_id)
    items = []
    for s in rows:
        if _derived_presence(s, now) in ("on_break", "offline"):
            continue
        view = _start_view(ctx, s["user_id"], body.reason, viewer_name, now)
        items.append({**view, "subject_user_id": s["user_id"], "name": s["name"], "camera": s["camera"], "screen": s["streaming"]})
    return ok({"livekit_url": ctx.settings.livekit_url, "expires_in_seconds": livekit.VIEW_TTL_SECONDS, "items": items,
               "subjects_notified": len(items)}, status=201)


# ------------------------------------------------------------------------------------------------ API-027
@router.post("/stream/view/{view_id}/end")
def end_view(view_id: uuid.UUID, ctx: SessionCtx):
    view = ctx.db.one("SELECT id, org_id, subject_user_id, started_at, ended_at FROM ems.stream_views WHERE id = :v AND viewer_id = :me",
                      v=view_id, me=ctx.user_id)
    if view is None:
        raise not_found("View")
    if view["ended_at"] is None:
        # The view is recorded as ended only once the viewer is really disconnected; on failure the client retries.
        try:
            livekit.remove_viewer(livekit.MediaConfig.of(ctx.settings), view["org_id"], view["subject_user_id"], view_id)
        except livekit.MediaError as exc:
            raise ApiError("MEDIA_UNAVAILABLE", "Could not close the live view right now. Try again in a moment.") from exc
        ctx.db.execute("UPDATE ems.stream_views SET ended_at = now() WHERE id = :v AND ended_at IS NULL", v=view_id)
        view["ended_at"] = ctx.db.scalar("SELECT ended_at FROM ems.stream_views WHERE id = :v", v=view_id)   # or the sweep's time
        ctx.audit("room.stream_view_ended", "stream_view", view_id, ["ended_at"])
    return ok({"view_id": view_id, "started_at": view["started_at"], "ended_at": view["ended_at"],
               "seconds": int((view["ended_at"] - view["started_at"]).total_seconds())})


# ------------------------------------------------------------------------------------------------ API-028
@router.get("/my-viewers")
def my_viewers(ctx: EitherCtx, from_: Annotated[dt.date | None, Query(alias="from")] = None,
               to: Annotated[dt.date | None, Query()] = None):
    ctx.require("room.self")
    cal = ctx.calendar
    to = to or cal.local_date()
    from_ = from_ or to - dt.timedelta(days=6)
    if from_ > to or (to - from_).days > 366:
        raise invalid("Choose a date range of at most one year.", {"from": "Must be on or before 'to'."})
    start, end = cal.day_bounds(from_)[0], cal.day_bounds(to)[1]
    rows = ctx.db.all("SELECT v.id, u.name AS viewer, v.reason, v.started_at, v.ended_at FROM ems.stream_views v "
                      "JOIN ems.users u ON u.id = v.viewer_id WHERE v.subject_user_id = :me AND v.started_at >= :s AND v.started_at < :e "
                      "ORDER BY v.started_at DESC", me=ctx.user_id, s=start, e=end)
    return ok({"items": [{"view_id": r["id"], "viewer": r["viewer"], "reason": r["reason"], "started_at": r["started_at"],
                          "seconds": int((r["ended_at"] - r["started_at"]).total_seconds()) if r["ended_at"] else None}
                         for r in rows]})
