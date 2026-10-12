"""LiveKit access tokens and viewer removal (livekit-api 1.2.1).

One LiveKit room per employee (DEC-005), so a viewer token reaches exactly one person. TTL and can_publish_data are
always set explicitly: the library defaults (6 h, data publishing allowed) are unsafe (LK-03).

A token's TTL only limits *joining*: a viewer who is already connected stays connected after it expires. So every way
a view can end (API-027, the worker sweep, consent withdrawn, a break, live view switched off, deactivation) removes the
viewer through the LiveKit room service. Each view has its own identity, `viewer:{view_id}`, so removing one view
never drops another view of the same employee.
"""
import asyncio
import datetime as dt
import os
import uuid
from dataclasses import dataclass

from livekit import api

from app.config import Settings
from app.platform.errors import ApiError

PUBLISH_TTL_SECONDS, VIEW_TTL_SECONDS = 600, 900
REMOVE_TIMEOUT_SECONDS = 5


class MediaError(RuntimeError):
    """The LiveKit room service could not be reached or refused the request; the caller retries later."""


@dataclass(frozen=True)
class MediaConfig:
    url: str
    api_key: str
    api_secret: str

    @property
    def configured(self) -> bool:
        return bool(self.url and self.api_key and self.api_secret)

    @classmethod
    def of(cls, settings: Settings) -> "MediaConfig":
        return cls(settings.livekit_url, settings.livekit_api_key, settings.livekit_api_secret)

    @classmethod
    def from_env(cls) -> "MediaConfig":
        """The worker does not load the API settings; it reads the same three variables (all or none)."""
        values = [os.environ.get(n, "").strip() for n in ("LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET")]
        if any(values) and not all(values):
            raise SystemExit("Set all of LIVEKIT_URL, LIVEKIT_API_KEY and LIVEKIT_API_SECRET, or none of them.")
        return cls(*values)


def room_name(org_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"ems-{org_id}-{user_id}"


def viewer_identity(view_id: uuid.UUID) -> str:
    return f"viewer:{view_id}"


def _require_configured(settings: Settings) -> None:
    if not settings.livekit_configured:
        raise ApiError("MEDIA_UNAVAILABLE", "Live screen sharing is not available right now. Presence keeps working.")


def publish_sources(camera: bool) -> list[str]:
    """Screen share always; the webcam only with the employee's webcam opt-in. Never the microphone."""
    return ["screen_share", "camera"] if camera else ["screen_share"]


def publish_token(settings: Settings, org_id: uuid.UUID, user_id: uuid.UUID, camera: bool = False) -> str:
    _require_configured(settings)
    grants = api.VideoGrants(room_join=True, room=room_name(org_id, user_id), can_publish=True, can_subscribe=False,
                             can_publish_data=False, can_publish_sources=publish_sources(camera))
    return (api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(f"employee:{user_id}").with_ttl(dt.timedelta(seconds=PUBLISH_TTL_SECONDS))
            .with_grants(grants).to_jwt())


def view_token(settings: Settings, org_id: uuid.UUID, subject_id: uuid.UUID, view_id: uuid.UUID) -> str:
    _require_configured(settings)
    grants = api.VideoGrants(room_join=True, room=room_name(org_id, subject_id), can_publish=False, can_subscribe=True,
                             can_publish_data=False)
    return (api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(viewer_identity(view_id)).with_ttl(dt.timedelta(seconds=VIEW_TTL_SECONDS))
            .with_grants(grants).to_jwt())


async def _remove(media: MediaConfig, room: str, identity: str) -> None:
    lk = api.LiveKitAPI(media.url, media.api_key, media.api_secret)
    try:
        await asyncio.wait_for(lk.room.remove_participant(api.RoomParticipantIdentity(room=room, identity=identity)),
                               REMOVE_TIMEOUT_SECONDS)
    finally:
        await lk.aclose()


def remove_viewer(media: MediaConfig, org_id: uuid.UUID, subject_id: uuid.UUID, view_id: uuid.UUID) -> None:
    """Disconnect one view. Returns when the viewer is gone (including "was never connected / already left");
    raises MediaError otherwise. Without a LiveKit configuration no view token can exist, so there is nothing to remove."""
    if not media.configured:
        return
    try:
        asyncio.run(_remove(media, room_name(org_id, subject_id), viewer_identity(view_id)))
    except api.TwirpError as exc:
        if exc.code == "not_found":                 # not in the room (left already, or the room is gone)
            return
        raise MediaError(f"LiveKit refused the removal: {exc.code}") from exc
    except Exception as exc:  # noqa: BLE001 - network errors, timeouts: the caller keeps the view open and retries
        raise MediaError("LiveKit could not be reached") from exc
