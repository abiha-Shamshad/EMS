"""LiveKit access tokens (livekit-api 1.2.1). The API never talks to LiveKit; it only signs short-lived tokens.

One LiveKit room per employee (DEC-005), so a viewer token reaches exactly one person. TTL and can_publish_data are
always set explicitly: the library defaults (6 h, data publishing allowed) are unsafe (LK-03).
"""
import datetime as dt
import uuid

from livekit import api

from app.config import Settings
from app.platform.errors import ApiError

PUBLISH_TTL_SECONDS, VIEW_TTL_SECONDS = 600, 900


def room_name(org_id: uuid.UUID, user_id: uuid.UUID) -> str:
    return f"ems-{org_id}-{user_id}"


def _require_configured(settings: Settings) -> None:
    if not settings.livekit_configured:
        raise ApiError("MEDIA_UNAVAILABLE", "Live screen sharing is not available right now. Presence keeps working.")


def publish_token(settings: Settings, org_id: uuid.UUID, user_id: uuid.UUID) -> str:
    _require_configured(settings)
    grants = api.VideoGrants(room_join=True, room=room_name(org_id, user_id), can_publish=True, can_subscribe=False,
                             can_publish_data=False, can_publish_sources=["screen_share"])
    return (api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(f"employee:{user_id}").with_ttl(dt.timedelta(seconds=PUBLISH_TTL_SECONDS))
            .with_grants(grants).to_jwt())


def view_token(settings: Settings, org_id: uuid.UUID, subject_id: uuid.UUID, viewer_id: uuid.UUID) -> str:
    _require_configured(settings)
    grants = api.VideoGrants(room_join=True, room=room_name(org_id, subject_id), can_publish=False, can_subscribe=True,
                             can_publish_data=False)
    return (api.AccessToken(settings.livekit_api_key, settings.livekit_api_secret)
            .with_identity(f"viewer:{viewer_id}").with_ttl(dt.timedelta(seconds=VIEW_TTL_SECONDS))
            .with_grants(grants).to_jwt())
