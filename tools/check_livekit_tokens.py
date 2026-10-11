"""Local check of the LiveKit token grants EMS issues (API-024 publish, API-026 view). No server needed.
Requires livekit-api 1.2.1 and PyJWT 2.15.1. Run: python tools/check_livekit_tokens.py"""
import datetime, jwt
from livekit import api

KEY, SECRET = "devkey", "local-check-secret-not-a-real-credential"
ROOM = "ems-org-6b0c-user-91aa"            # one LiveKit room per employee: a viewer token can only reach that employee

def decode(t):
    return jwt.decode(t, SECRET, algorithms=["HS256"], options={"verify_aud": False})

pub = (api.AccessToken(KEY, SECRET).with_identity("employee:91aa").with_ttl(datetime.timedelta(seconds=600))
       .with_grants(api.VideoGrants(room_join=True, room=ROOM, can_publish=True, can_subscribe=False,
                                    can_publish_data=False, can_publish_sources=["screen_share"])).to_jwt())
view = (api.AccessToken(KEY, SECRET).with_identity("viewer:ceo").with_ttl(datetime.timedelta(seconds=900))
        .with_grants(api.VideoGrants(room_join=True, room=ROOM, can_publish=False, can_subscribe=True,
                                     can_publish_data=False)).to_jwt())
p, v = decode(pub), decode(view)
assert p["video"] == {"roomJoin": True, "room": ROOM, "canPublish": True, "canSubscribe": False,
                      "canPublishData": False, "canPublishSources": ["screen_share"]}, p["video"]
assert p["exp"] - p["nbf"] == 600
assert v["video"]["canPublish"] is False and v["video"]["canSubscribe"] is True and v["video"]["room"] == ROOM
assert v["exp"] - v["nbf"] == 900
# Default (no with_ttl / no can_publish_data) would give a 6 h token that can publish data - EMS always sets both.
d = decode(api.AccessToken(KEY, SECRET).with_identity("x").with_grants(api.VideoGrants(room_join=True, room=ROOM)).to_jwt())
assert d["exp"] - d["nbf"] == 21600 and d["video"].get("canPublishData") is True
print("LK-01 publish grant PASS\nLK-02 view grant PASS\nLK-03 defaults are unsafe and overridden PASS")
