"""Webcam in the Employee Room (db/006): separate opt-in, camera state from heartbeats, the CEO video grid, and the
extension attaching to a web check-in."""
import jwt
import pytest
from conftest import Api, make_settings

from app.main import create_app
from app.room import livekit
from app.room import router as room_router
from worker import jobs

SECRET = "local-test-secret-not-a-real-credential"
LIVEKIT = {"livekit_url": "wss://media.example", "livekit_api_key": "devkey", "livekit_api_secret": SECRET}


@pytest.fixture
def room(company, database, admin_sql, monkeypatch):
    monkeypatch.setattr(room_router.ratelimit, "hit", lambda *a, **k: None)
    monkeypatch.setattr(livekit, "remove_viewer", lambda *a, **k: None)
    co = company(roles=("coo", "manager", "employee"))
    admin_sql("UPDATE ems.organizations SET live_view_enabled = true WHERE id = %s", co["org_id"])
    media = create_app(make_settings(database, **LIVEKIT))

    def as_media(role):
        a = Api(media)
        a.client.cookies, a.user_id = co[role].client.cookies, co[role].user_id
        return a
    people = {r: as_media(r) for r in ("coo", "manager", "employee")}

    def checked_in(role, webcam: bool, screen: bool = False, camera: bool = True):
        a = people[role]
        assert a.post("/api/v1/room/consent", {"policy_version": 1, "accept": True, "webcam": webcam}).status_code == 200
        c = a.post("/api/v1/room/check-in", {"device": {"kind": "chrome_extension"}}).json()["data"]
        a.ext_token, a.session = c["extension_token"], c["session_id"]
        r = a.post("/api/v1/room/heartbeat", {"session_id": a.session, "sent_at": "2026-10-13T05:00:00Z", "idle_state": "active",
                                              "streaming": screen, "camera": camera}, ext=True)
        assert r.status_code == 200, r.text
        return a
    return {"co": co, "people": people, "checked_in": checked_in}


def test_webcam_needs_its_own_opt_in(room):
    emp = room["checked_in"]("employee", webcam=False)
    grid = room["people"]["coo"].get("/api/v1/room/live").json()["data"]["items"]
    assert next(i for i in grid if i["name"] == "Bilal Ahmed")["camera"] == "off"           # reported camera ignored without opt-in
    denied = emp.post("/api/v1/room/stream/publish-token", {"session_id": emp.session, "camera": True}, ext=True)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "CONSENT_REQUIRED"

    consent = emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": True, "webcam": True}).json()["data"]
    assert "live_webcam_while_checked_in" in consent["covers"] and "webcam" not in consent["excludes"] and "microphone" in consent["excludes"]
    token = emp.post("/api/v1/room/stream/publish-token", {"session_id": emp.session, "camera": True}, ext=True).json()["data"]
    assert token["grants"]["can_publish_sources"] == ["screen_share", "camera"]
    claims = jwt.decode(token["token"], SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert claims["video"]["canPublishSources"] == ["screen_share", "camera"] and claims["video"]["canPublishData"] is False
    screen_only = emp.post("/api/v1/room/stream/publish-token", {"session_id": emp.session}, ext=True).json()["data"]
    assert screen_only["grants"]["can_publish_sources"] == ["screen_share"]


def test_camera_state_pauses_on_breaks(room, admin_sql):
    emp = room["checked_in"]("employee", webcam=True)
    coo = room["people"]["coo"]
    assert next(i for i in coo.get("/api/v1/room/live").json()["data"]["items"] if i["name"] == "Bilal Ahmed")["camera"] == "live"
    emp.post("/api/v1/room/breaks", {"session_id": emp.session, "kind": "short", "minutes": 10}, ext=True)
    assert admin_sql("SELECT camera FROM ems.work_sessions WHERE id = %s", emp.session)[0][0] is False
    emp.post("/api/v1/room/heartbeat", {"session_id": emp.session, "sent_at": "2026-10-13T05:01:00Z", "idle_state": "active",
                                        "streaming": False, "camera": True}, ext=True)
    assert admin_sql("SELECT camera FROM ems.work_sessions WHERE id = %s", emp.session)[0][0] is False      # not while on a break
    emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": False})
    assert admin_sql("SELECT count(*) FROM ems.stream_consents WHERE user_id = %s AND revoked_at IS NULL", emp.user_id)[0][0] == 0


def test_ceo_grid_opens_one_logged_view_per_live_employee(room, admin_sql):
    room["checked_in"]("employee", webcam=True)                         # webcam only
    room["checked_in"]("manager", webcam=False, screen=True, camera=False)   # screen only
    coo = room["people"]["coo"]
    assert room["co"]["employee"].post("/api/v1/room/stream/view-grid", {"reason": "Morning check"}).status_code == 403
    assert coo.post("/api/v1/room/stream/view-grid", {"reason": "x"}).status_code == 400

    grid = coo.post("/api/v1/room/stream/view-grid", {"reason": "Morning check"})
    assert grid.status_code == 201, grid.text
    data = grid.json()["data"]
    assert data["subjects_notified"] == 2 and data["expires_in_seconds"] == 900
    by_name = {i["name"]: i for i in data["items"]}
    assert (by_name["Bilal Ahmed"]["camera"], by_name["Bilal Ahmed"]["screen"]) == (True, False)
    assert (by_name["Usman Tariq"]["camera"], by_name["Usman Tariq"]["screen"]) == (False, True)
    claims = jwt.decode(by_name["Bilal Ahmed"]["token"], SECRET, algorithms=["HS256"], options={"verify_aud": False})
    assert claims["sub"] == f"viewer:{by_name['Bilal Ahmed']['view_id']}" and claims["video"]["canPublish"] is False
    assert admin_sql("SELECT count(*) FROM ems.stream_views WHERE org_id = %s AND reason = 'Morning check'", room["co"]["org_id"])[0][0] == 2
    notes = [n["title"] for n in room["co"]["employee"].get("/api/v1/notifications").json()["data"]["items"]]
    assert "Zain Coo is viewing you live: Morning check" in notes

    admin_sql("UPDATE ems.organizations SET live_view_enabled = false WHERE id = %s", room["co"]["org_id"])
    assert coo.post("/api/v1/room/stream/view-grid", {"reason": "Morning check"}).status_code == 403


def test_camera_alone_keeps_a_view_open_in_the_sweep(room, worker_engine, admin_sql):
    emp = room["checked_in"]("employee", webcam=True)
    view = room["people"]["coo"].post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id, "reason": "Quick check"}).json()["data"]
    jobs.tick(worker_engine, livekit.MediaConfig("", "", ""))
    assert admin_sql("SELECT ended_at FROM ems.stream_views WHERE id = %s", view["view_id"])[0][0] is None
    admin_sql("UPDATE ems.work_sessions SET camera = false WHERE id = %s", emp.session)
    jobs.tick(worker_engine, livekit.MediaConfig("", "", ""))
    assert admin_sql("SELECT ended_at FROM ems.stream_views WHERE id = %s", view["view_id"])[0][0] is not None


def test_extension_attaches_to_a_web_check_in(room):
    emp = room["people"]["employee"]
    web = emp.post("/api/v1/room/check-in", {"device": {"kind": "web"}}).json()["data"]
    again_web = emp.post("/api/v1/room/check-in", {"device": {"kind": "web"}}).json()["data"]
    assert again_web["already_open"] and "extension_token" not in again_web
    ext = emp.post("/api/v1/room/check-in", {"device": {"kind": "chrome_extension"}}).json()["data"]
    assert ext["session_id"] == web["session_id"] and ext["extension_token"].startswith("ext_")
    emp.ext_token = ext["extension_token"]
    beat = emp.post("/api/v1/room/heartbeat", {"session_id": web["session_id"], "sent_at": "2026-10-13T05:00:00Z", "idle_state": "active",
                                               "streaming": False}, ext=True)
    assert beat.status_code == 200
    second = emp.post("/api/v1/room/check-in", {"device": {"kind": "chrome_extension"}}).json()["data"]
    old = emp.post("/api/v1/room/heartbeat", {"session_id": web["session_id"], "sent_at": "2026-10-13T05:01:00Z", "idle_state": "active",
                                              "streaming": False}, ext=True)
    assert old.status_code == 401                                         # the earlier token was revoked
    assert second["extension_token"] != ext["extension_token"]
