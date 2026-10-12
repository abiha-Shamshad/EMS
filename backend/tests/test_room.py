"""Employee Room server (TASK-007, TASK-011 API part): fixture-day totals, consent, breaks, views, concurrency (TEST-006)."""
import datetime as dt
import threading

import pytest
from conftest import Api, assert_contract, make_settings

from app.main import create_app
from app.room import router as room_router

UTC = dt.UTC
DAY = dt.datetime(2026, 10, 12, 4, 2, tzinfo=UTC)          # Monday 12 Oct 2026, 09:02 PKT (fixture, Section 19.4)


@pytest.fixture
def clock(monkeypatch):
    """Controllable 'now' for the Room endpoints; per-session heartbeat rate limits are bypassed for simulated time."""
    state = {"now": DAY}
    monkeypatch.setattr(room_router, "utcnow", lambda: state["now"])
    monkeypatch.setattr(room_router.ratelimit, "hit", lambda *a, **k: None)
    return state


def _task(co, assignee) -> str:
    project = co["manager"].post("/api/v1/projects", {"name": "Platform", "billing_type": "internal"}, idem=True).json()["data"]["id"]
    return co["manager"].post(f"/api/v1/projects/{project}/tasks", {"title": "Auth API", "assignee_id": assignee}, idem=True).json()["data"]["id"]


def test_fixture_day_totals(company, clock, admin_sql):
    """TASK-007 expect: check-out totals active 412, idle 38, on_break 45, offline 48 (543 minutes, 09:02-18:05)."""
    co = company(roles=("manager", "employee"))
    bilal = co["employee"]
    task = _task(co, bilal.user_id)
    consent = bilal.post("/api/v1/room/consent", {"policy_version": 1, "accept": True})
    assert_contract("API-017", consent, expect_status=200)

    checked_in = assert_contract("API-018", bilal.post("/api/v1/room/check-in", {"device": {"kind": "chrome_extension",
                                 "extension_version": "1.0.0"}, "task_id": task}), expect_status=201)
    assert checked_in["minutes_late"] == 0 and checked_in["streaming_required"] is False      # live view is off (OD-02)
    bilal.ext_token, session = checked_in["extension_token"], checked_in["session_id"]
    # The token expiry is computed from the simulated clock but checked by PostgreSQL against the real one.
    admin_sql("UPDATE ems.extension_tokens SET expires_at = now() + interval '1 day' WHERE session_id = %s", session)

    def beat(at: dt.datetime, state: str):
        clock["now"] = at
        r = bilal.post("/api/v1/room/heartbeat", {"session_id": session, "sent_at": at.isoformat(), "idle_state": state,
                                                  "streaming": False}, ext=True)
        assert r.status_code == 200, r.text
        return r

    t = DAY
    for minute in range(1, 200):                          # 09:03 .. 12:21 active
        beat(t + dt.timedelta(minutes=minute), "active")
    for minute in range(200, 239):                        # 12:22 .. 13:00 idle (no input for 5 min); heartbeats never pause
        beat(t + dt.timedelta(minutes=minute), "idle")
    clock["now"] = t + dt.timedelta(minutes=238)          # 13:00 lunch, within the 60-minute allowance
    brk = assert_contract("API-021", bilal.post("/api/v1/room/breaks", {"session_id": session, "kind": "lunch", "minutes": 45},
                                                ext=True), expect_status=201)
    assert brk["status"] == "active" and brk["approval"] == "auto_approved_by_policy"
    for minute in range(239, 283):                        # heartbeats during the break report on_break
        assert beat(t + dt.timedelta(minutes=minute), "active").json()["data"]["presence"] == "on_break"
    clock["now"] = t + dt.timedelta(minutes=283)          # 13:45 back
    ended = assert_contract("API-023", bilal.post(f"/api/v1/room/breaks/{brk['break_id']}/end", ext=True), expect_status=200)
    assert ended["minutes"] == 45 and ended["over_allowance_minutes"] == 0
    for minute in range(283, 494):                        # 13:45 .. 17:16 active
        beat(t + dt.timedelta(minutes=minute), "active")
    beat(t + dt.timedelta(minutes=494, seconds=30), "active")                 # last heartbeat 17:16:30, then silence

    clock["now"] = dt.datetime(2026, 10, 12, 13, 5, tzinfo=UTC)               # 18:05 check-out from the web app
    out = assert_contract("API-020", bilal.post("/api/v1/room/check-out", {"session_id": session, "note": "Auth API done"}), expect_status=200)
    assert {k: out["totals_minutes"][k] for k in ("active", "idle", "on_break", "offline")} == \
        {"active": 412, "idle": 38, "on_break": 45, "offline": 48}
    assert out["time_entries_created"] == 1
    board = co["manager"].get(f"/api/v1/projects/{co['manager'].get('/api/v1/projects').json()['data']['items'][0]['id']}/board").json()
    assert board["data"]["columns"]["todo"][0]["minutes_logged"] == 412      # Room time became a `room` time entry
    after = bilal.post("/api/v1/room/heartbeat", {"session_id": session, "sent_at": clock["now"].isoformat(), "idle_state": "active",
                                                  "streaming": False}, ext=True)
    assert after.status_code == 401                                          # token revoked at check-out
    repeat = bilal.post("/api/v1/room/check-out", {"session_id": session})
    assert repeat.status_code == 200 and repeat.json()["data"]["totals_minutes"]["active"] == 412


def test_check_in_repeat_leave_and_concurrency(company, admin_sql):
    co = company(roles=("manager", "employee"))
    usman = co["manager"]
    results, threads = [], []

    def go():
        results.append(usman.post("/api/v1/room/check-in", {}).status_code)
    for _ in range(20):                                   # TEST-006 check-in part
        threads.append(threading.Thread(target=go))
    for th in threads:
        th.start()
    for th in threads:
        th.join()
    assert sorted(results) == [200] * 19 + [201]
    open_sessions = admin_sql("SELECT count(*) FROM ems.work_sessions WHERE user_id = %s AND state = 'open'", usman.user_id)
    assert open_sessions[0][0] == 1
    repeat = usman.post("/api/v1/room/check-in", {})
    assert repeat.json()["data"]["already_open"] is True

    admin_sql("INSERT INTO ems.leave_requests (id, org_id, user_id, kind, period, status) VALUES (gen_random_uuid(), %s, %s, 'annual', "
              "daterange((now() AT TIME ZONE 'Asia/Karachi')::date, (now() AT TIME ZONE 'Asia/Karachi')::date, '[]'), 'approved')",
              co["org_id"], co["employee"].user_id)
    blocked = co["employee"].post("/api/v1/room/check-in", {})
    assert_contract("API-018", blocked, expect_status=403)
    assert blocked.json()["error"]["code"] == "ON_APPROVED_LEAVE"


def test_consent_versions_and_withdrawal(company, admin_sql):
    co = company(roles=("employee",))
    emp = co["employee"]
    assert emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": True}).status_code == 200
    admin_sql("UPDATE ems.organizations SET room_policy_version = 2 WHERE id = %s", co["org_id"])   # HR published a new notice
    outdated = emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": True})
    assert_contract("API-017", outdated, expect_status=409)
    assert outdated.json()["error"]["details"] == {"current_version": 2}
    assert emp.post("/api/v1/room/consent", {"policy_version": 2, "accept": True}).json()["data"]["consented_at"]
    withdrawn = emp.post("/api/v1/room/consent", {"policy_version": 2, "accept": False}).json()["data"]
    assert withdrawn["stream_stopped"] is True


def test_break_above_allowance_needs_decision(company, drain):
    co = company(roles=("manager", "employee"))
    emp, mgr = co["employee"], co["manager"]
    session = emp.post("/api/v1/room/check-in", {}).json()["data"]["session_id"]
    req = emp.post("/api/v1/room/breaks", {"session_id": session, "kind": "personal", "minutes": 90}).json()["data"]
    assert req["status"] == "requested" and req["approval"] == "manager_required"
    drain()
    titles = [n["title"] for n in mgr.get("/api/v1/notifications").json()["data"]["items"]]
    assert any("90-minute personal break" in t for t in titles)
    assert emp.post(f"/api/v1/room/breaks/{req['break_id']}/decision", {"decision": "approved"}).status_code == 403   # not own
    decided = assert_contract("API-022", mgr.post(f"/api/v1/room/breaks/{req['break_id']}/decision", {"decision": "approved"}),
                              expect_status=200)
    assert decided["status"] == "active"
    again = mgr.post(f"/api/v1/room/breaks/{req['break_id']}/decision", {"decision": "rejected"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "ALREADY_DECIDED"


def test_live_grid_and_audited_views(app, company, database, admin_sql, drain):
    co = company(roles=("coo", "employee"))
    coo, emp = co["coo"], co["employee"]
    assert emp.get("/api/v1/room/live").status_code == 403
    emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": True})
    checked = emp.post("/api/v1/room/check-in", {}).json()["data"]
    emp.ext_token = checked["extension_token"]
    grid = assert_contract("API-025", coo.get("/api/v1/room/live"), expect_status=200)
    assert grid["counts"]["checked_in"] == 1 and grid["items"][0]["stream"] == "disabled"

    off = coo.post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id, "reason": "Daily stand-up check"})
    assert off.status_code == 403                                             # live_view_enabled = false until OD-02
    admin_sql("UPDATE ems.organizations SET live_view_enabled = true WHERE id = %s", co["org_id"])
    no_media = emp.post("/api/v1/room/stream/publish-token", {"session_id": checked["session_id"]}, ext=True)
    assert_contract("API-024", no_media, expect_status=503)                  # LiveKit not configured: never a fake token

    media = create_app(make_settings(database, livekit_url="wss://media.example", livekit_api_key="devkey",
                                     livekit_api_secret="local-test-secret-not-a-real-credential"))
    emp_m, coo_m = Api(media), Api(media)
    emp_m.client.cookies, coo_m.client.cookies = emp.client.cookies, coo.client.cookies
    emp_m.ext_token = emp.ext_token
    token = assert_contract("API-024", emp_m.post("/api/v1/room/stream/publish-token", {"session_id": checked["session_id"]}, ext=True),
                            expect_status=200)
    assert token["room"] == f"ems-{co['org_id']}-{emp.user_id}" and token["expires_in_seconds"] == 600
    not_live = coo_m.post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id, "reason": "Daily stand-up check"})
    assert_contract("API-026", not_live, expect_status=409)
    emp_m.post("/api/v1/room/heartbeat", {"session_id": checked["session_id"], "sent_at": "2026-10-12T05:30:00Z", "idle_state": "active",
                                          "streaming": True}, ext=True)
    short = coo_m.post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id, "reason": "x"})
    assert short.status_code == 400
    view = assert_contract("API-026", coo_m.post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id,
                                                                              "reason": "Daily stand-up check"}), expect_status=201)
    assert view["grants"]["can_publish"] is False and view["subject_notified"] is True
    notices = emp.get("/api/v1/notifications").json()["data"]["items"]
    assert notices[0]["title"] == "Zain Coo is viewing your screen"          # G5: written with the view, not later
    seen = assert_contract("API-028", emp.get("/api/v1/room/my-viewers"), expect_status=200)
    assert seen["items"][0]["reason"] == "Daily stand-up check" and seen["items"][0]["seconds"] is None
    closed = assert_contract("API-027", coo.post(f"/api/v1/room/stream/view/{view['view_id']}/end"), expect_status=200)
    assert closed["seconds"] >= 0
    assert emp.post(f"/api/v1/room/stream/view/{view['view_id']}/end").status_code == 404          # only the viewer
