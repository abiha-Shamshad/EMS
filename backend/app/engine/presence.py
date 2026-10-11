"""Presence derivation from extension heartbeats (proposed path: backend/app/engine/presence.py).

The extension sends a heartbeat every 30 s with the chrome.idle state ('active' | 'idle' | 'locked')
and whether a break is active. The server turns heartbeats into closed presence segments.
A gap longer than OFFLINE_AFTER seconds between heartbeats is an 'offline' segment.
"""
from datetime import datetime, timedelta

HEARTBEAT_SECONDS = 30
OFFLINE_AFTER = 90


def segments(heartbeats: list[dict], session_end: datetime) -> list[dict]:
    """heartbeats: [{"at": datetime, "state": "active|idle|locked", "on_break": bool}] sorted by time.
    Returns [{"presence", "start", "end"}] covering first heartbeat .. session_end, adjacent equal states merged."""
    out: list[dict] = []

    def add(p, s, e):
        if e <= s:
            return
        if out and out[-1]["presence"] == p and out[-1]["end"] == s:
            out[-1]["end"] = e
        else:
            out.append({"presence": p, "start": s, "end": e})

    for i, hb in enumerate(heartbeats):
        nxt = heartbeats[i + 1]["at"] if i + 1 < len(heartbeats) else session_end
        state = "on_break" if hb.get("on_break") else hb["state"]
        gap = (nxt - hb["at"]).total_seconds()
        if gap > OFFLINE_AFTER:
            add(state, hb["at"], hb["at"] + timedelta(seconds=HEARTBEAT_SECONDS))
            add("offline", hb["at"] + timedelta(seconds=HEARTBEAT_SECONDS), nxt)
        else:
            add(state, hb["at"], nxt)
    return out


def totals(segs: list[dict]) -> dict[str, int]:
    """Minutes per presence state, rounded down."""
    t: dict[str, float] = {}
    for s in segs:
        t[s["presence"]] = t.get(s["presence"], 0) + (s["end"] - s["start"]).total_seconds()
    return {k: int(v // 60) for k, v in t.items()}


def current_presence(last_heartbeat_at: datetime | None, last_state: str, on_break: bool, now: datetime) -> str:
    if last_heartbeat_at is None or (now - last_heartbeat_at).total_seconds() > OFFLINE_AFTER:
        return "offline"
    return "on_break" if on_break else last_state
