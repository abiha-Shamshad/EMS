"""Pre-pilot review fixes: outbox stall, late check-in token, double billing, trusted proxies, role escalation,
live-viewer disconnects, leakage tiles before the first scan."""
import datetime as dt
import threading

import jwt
import pytest
from conftest import Api, assert_contract, make_settings, unique

from app import config, serve
from app.main import create_app
from app.platform.timeutil import Calendar
from app.room import livekit
from app.room import router as room_router
from worker import jobs
from worker.main import MAX_ATTEMPTS, OutboxLoop
from worker.registry import HANDLERS

UTC = dt.UTC
LIVEKIT = {"livekit_url": "wss://media.example", "livekit_api_key": "devkey", "livekit_api_secret": "local-test-secret-not-a-real-credential"}


# ------------------------------------------------------------------------------------------------ worker stall
def test_failing_events_cannot_stall_the_outbox(company, worker_engine, admin_sql):
    co = company(roles=())
    org = co["org_id"]
    for _ in range(101):                                            # more failing events than one scan batch, all older
        admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload, created_at) "
                  "VALUES (gen_random_uuid(), %s, 'test.poison', '{}', now() - interval '1 hour')", org)
    good = admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (gen_random_uuid(), %s, 'test.good', '{}') "
                     "RETURNING id", org)[0][0]
    handled = []

    def boom(db, event):
        raise RuntimeError("handler bug")
    HANDLERS["test.poison"], HANDLERS["test.good"] = [boom], [lambda db, e: handled.append(e.id)]
    try:
        loop = OutboxLoop(worker_engine)
        for _ in range(5):
            loop.run_once()
            if handled:
                break
        assert handled == [good]                                    # the healthy event got through
        assert admin_sql("SELECT count(*) FROM ems.outbox_events WHERE org_id = %s AND routing_key = 'test.poison' "
                         "AND attempts >= 1 AND next_attempt_at > now() AND NOT dead", org)[0][0] == 101

        # Retry state lives in the database: a new process (restart) continues the count and stops at the limit.
        one = admin_sql("SELECT id FROM ems.outbox_events WHERE org_id = %s AND routing_key = 'test.poison' LIMIT 1", org)[0][0]
        admin_sql("UPDATE ems.outbox_events SET attempts = %s, next_attempt_at = now() WHERE id = %s", MAX_ATTEMPTS - 1, one)
        calls = []
        HANDLERS["test.poison"] = [lambda db, e: (calls.append(e.id), boom(db, e))]
        restarted = OutboxLoop(worker_engine)
        restarted.run_once()
        assert calls == [one]
        assert admin_sql("SELECT attempts, dead, published_at FROM ems.outbox_events WHERE id = %s", one)[0] == (MAX_ATTEMPTS, True, None)
        admin_sql("UPDATE ems.outbox_events SET next_attempt_at = now() WHERE id = %s", one)
        restarted.run_once()
        assert calls == [one]                                       # dead: never picked up again
    finally:
        HANDLERS.pop("test.poison"), HANDLERS.pop("test.good")
        admin_sql("UPDATE ems.outbox_events SET published_at = now() WHERE routing_key IN ('test.poison', 'test.good')")


# ------------------------------------------------------------------------------------------------ extension token
@pytest.mark.parametrize(("local_check_in", "hours"), [("19:30", 2.0), ("09:00", 11.0), ("04:00", 14.0)])
def test_extension_token_lifetime(local_check_in, hours):
    from app.room.service import extension_token_expiry
    cal = Calendar("Asia/Karachi", {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "18:00"})
    now = cal.at_local(dt.date(2026, 10, 12), dt.time.fromisoformat(local_check_in))
    assert extension_token_expiry(cal, now) - now == dt.timedelta(hours=hours)


# ------------------------------------------------------------------------------------------------ double billing
def test_time_entries_cannot_be_invoiced_twice(company, admin_sql):
    co = company(roles=("manager", "cfo"))
    mgr, cfo = co["manager"], co["cfo"]
    contact = mgr.post("/api/v1/contacts", {"name": "Ali Raza", "email": f"ali.{unique()}@northwind.example", "source": "referral",
                                            "company": {"name": "Northwind", "domain": f"nw-{unique()}.example"}}, idem=True).json()["data"]
    deal = mgr.post("/api/v1/deals", {"contact_id": contact["id"], "title": "Site", "amount": "900.00", "currency": "USD",
                                      "expected_close": "2026-10-10"}, idem=True).json()["data"]
    won = mgr.post(f"/api/v1/deals/{deal['id']}/win", {"expected_version": 1}, idem=True).json()["data"]
    task = mgr.post(f"/api/v1/projects/{won['project']['id']}/tasks", {"title": "Build"}, idem=True).json()["data"]["id"]
    entries = [str(r[0]) for r in admin_sql(
        "INSERT INTO ems.time_entries (id, org_id, task_id, user_id, started_at, minutes, source, billable) "
        "SELECT gen_random_uuid(), %s, %s, %s, now() - make_interval(hours => g), 60, 'manual', true FROM generate_series(1, 3) g "
        "RETURNING id", co["org_id"], task, mgr.user_id)]
    codes = []

    def bill():
        codes.append(cfo.post("/api/v1/invoices", {"client_id": won["client"]["id"], "number": f"INV-{unique()}", "amount": "300.00",
                                                   "currency": "USD", "issued_on": "2026-10-05", "due_on": "2026-10-19",
                                                   "time_entry_ids": entries}, idem=True).status_code)
    threads = [threading.Thread(target=bill) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201, 400, 400, 400, 400]
    assert admin_sql("SELECT count(DISTINCT invoice_id), count(*) FILTER (WHERE invoice_id IS NULL) FROM ems.time_entries "
                     "WHERE id = ANY(%s::uuid[])", entries)[0] == (1, 0)
    assert admin_sql("SELECT count(*) FROM ems.invoices WHERE client_id = %s", won["client"]["id"])[0][0] == 1


# ------------------------------------------------------------------------------------------------ trusted proxies
@pytest.fixture
def env(monkeypatch):
    for name, value in {"DATABASE_URL": "postgresql+psycopg://ems_app@localhost/ems", "APP_BASE_URL": "https://app.example",
                        "CSRF_SECRET": "ab" * 32, "FORWARDED_ALLOW_IPS": "10.0.0.0/16"}.items():
        monkeypatch.setenv(name, value)
    for name in ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "LIVEKIT_URL", "LIVEKIT_API_KEY", "LIVEKIT_API_SECRET",
                 "EMAIL_PROVIDER", "AI_REPHRASER"):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.mark.parametrize("value", [None, "", "*", "10.0.0.0/16, *", "lb.internal"])
def test_forwarded_allow_ips_is_required_and_never_star(env, value):
    if value is None:
        env.delenv("FORWARDED_ALLOW_IPS")
    else:
        env.setenv("FORWARDED_ALLOW_IPS", value)
    with pytest.raises(config.ConfigError, match="FORWARDED_ALLOW_IPS"):
        config.load_settings()


def test_forwarded_allow_ips_reaches_uvicorn(env, monkeypatch):
    env.setenv("FORWARDED_ALLOW_IPS", " 10.0.0.0/16 , 172.31.4.7 ")
    settings = config.load_settings()
    assert settings.forwarded_allow_ips == "10.0.0.0/16,172.31.4.7"
    seen = {}
    monkeypatch.setattr(serve, "get_settings", lambda: settings)
    monkeypatch.setattr(serve.uvicorn, "run", lambda app, **kw: seen.update(app=app, **kw))
    serve.main()
    assert seen["app"] == "app.main:app" and seen["proxy_headers"] is True and seen["forwarded_allow_ips"] == "10.0.0.0/16,172.31.4.7"


# ------------------------------------------------------------------------------------------------ role escalation
def _version(co, user_id) -> int:
    members = co["ceo"].get("/api/v1/members", params={"limit": 100}).json()["data"]["items"]
    return next(m["version"] for m in members if m["user_id"] == user_id)


def test_hr_cannot_grant_leadership_or_change_own_role(company):
    co = company(roles=("hr", "employee"))
    ceo, hr, emp = co["ceo"], co["hr"], co["employee"].user_id
    for role in ("cto", "cfo", "coo", "hr"):
        own = hr.patch(f"/api/v1/members/{hr.user_id}", {"expected_version": _version(co, hr.user_id), "role": role})
        assert_contract("API-014", own, expect_status=403)
    for role in ("cto", "cfo", "coo"):
        r = hr.patch(f"/api/v1/members/{emp}", {"expected_version": _version(co, emp), "role": role})
        assert_contract("API-014", r, expect_status=403)
        invite = hr.post("/api/v1/invitations", {"invites": [{"email": f"{role}.{unique()}@acme.example", "role": role}]}, idem=True)
        assert_contract("API-011", invite, expect_status=403)
    assert hr.patch(f"/api/v1/members/{emp}", {"expected_version": _version(co, emp), "role": "manager"}).status_code == 200
    assert hr.post("/api/v1/invitations", {"invites": [{"email": f"e.{unique()}@acme.example", "role": "employee"}]},
                   idem=True).status_code == 201
    assert ceo.patch(f"/api/v1/members/{emp}", {"expected_version": _version(co, emp), "role": "cfo"}).status_code == 200
    assert ceo.post("/api/v1/invitations", {"invites": [{"email": f"c.{unique()}@acme.example", "role": "cto"}]},
                    idem=True).status_code == 201
    assert ceo.patch(f"/api/v1/members/{ceo.user_id}", {"expected_version": _version(co, ceo.user_id), "role": "cto"}).status_code == 403


# ------------------------------------------------------------------------------------------------ live viewers
@pytest.fixture
def live(company, database, admin_sql, monkeypatch):
    """A company with live view on, a consenting employee sharing their screen, and a recorder for LiveKit removals."""
    monkeypatch.setattr(room_router.ratelimit, "hit", lambda *a, **k: None)
    removals, state = [], {"fail": False}

    def remove(media, org_id, subject_id, view_id):
        if state["fail"]:
            raise livekit.MediaError("unreachable")
        removals.append(str(view_id))
    monkeypatch.setattr(livekit, "remove_viewer", remove)

    co = company(roles=("coo", "employee"))
    admin_sql("UPDATE ems.organizations SET live_view_enabled = true WHERE id = %s", co["org_id"])
    media = create_app(make_settings(database, **LIVEKIT))
    emp, coo = Api(media), Api(media)
    emp.client.cookies, coo.client.cookies = co["employee"].client.cookies, co["coo"].client.cookies
    emp.user_id, coo.user_id = co["employee"].user_id, co["coo"].user_id
    checked = emp.post("/api/v1/room/check-in", {}).json()["data"]
    emp.ext_token = checked["extension_token"]

    def share() -> None:
        assert emp.post("/api/v1/room/consent", {"policy_version": 1, "accept": True}).status_code == 200
        r = emp.post("/api/v1/room/heartbeat", {"session_id": checked["session_id"], "sent_at": "2026-10-12T05:30:00Z",
                                                "idle_state": "active", "streaming": True}, ext=True)
        assert r.status_code == 200, r.text

    def open_view() -> str:
        share()
        r = coo.post("/api/v1/room/stream/view", {"subject_user_id": emp.user_id, "reason": "Daily stand-up check"})
        assert r.status_code == 201, r.text
        return r.json()["data"]

    def ended(view_id) -> bool:
        return admin_sql("SELECT ended_at FROM ems.stream_views WHERE id = %s", view_id)[0][0] is not None
    return {"co": co, "emp": emp, "coo": coo, "session": checked["session_id"], "open_view": open_view, "ended": ended,
            "removals": removals, "state": state}


def test_view_token_identity_is_per_view(live):
    view = live["open_view"]()
    claims = jwt.decode(view["token"], LIVEKIT["livekit_api_secret"], algorithms=["HS256"], options={"verify_aud": False})
    assert claims["sub"] == f"viewer:{view['view_id']}"


def test_ending_a_view_removes_the_viewer_first(live):
    view = live["open_view"]()
    live["state"]["fail"] = True
    failed = live["coo"].post(f"/api/v1/room/stream/view/{view['view_id']}/end")
    assert failed.status_code == 503 and failed.json()["error"]["code"] == "MEDIA_UNAVAILABLE" and failed.json()["error"]["retryable"]
    assert not live["ended"](view["view_id"])                        # not recorded as ended while the viewer may still watch
    live["state"]["fail"] = False
    assert live["coo"].post(f"/api/v1/room/stream/view/{view['view_id']}/end").status_code == 200
    assert live["removals"] == [view["view_id"]] and live["ended"](view["view_id"])


def test_withdrawing_consent_disconnects_viewers(live):
    view = live["open_view"]()
    assert live["emp"].post("/api/v1/room/consent", {"policy_version": 1, "accept": False}).status_code == 200
    assert live["removals"] == [view["view_id"]] and live["ended"](view["view_id"])


def test_starting_a_break_disconnects_viewers(live):
    view = live["open_view"]()
    brk = live["emp"].post("/api/v1/room/breaks", {"session_id": live["session"], "kind": "short", "minutes": 15})
    assert brk.status_code == 201 and brk.json()["data"]["status"] == "active"
    assert live["removals"] == [view["view_id"]] and live["ended"](view["view_id"])


def test_sweep_disconnects_when_live_view_is_switched_off_and_retries_failures(live, worker_engine, admin_sql):
    view = live["open_view"]()
    admin_sql("UPDATE ems.organizations SET live_view_enabled = false WHERE id = %s", live["co"]["org_id"])
    media = livekit.MediaConfig(LIVEKIT["livekit_url"], LIVEKIT["livekit_api_key"], LIVEKIT["livekit_api_secret"])
    live["state"]["fail"] = True
    jobs.tick(worker_engine, media)
    assert not live["ended"](view["view_id"])                        # removal failed: still open, retried next minute
    live["state"]["fail"] = False
    jobs.tick(worker_engine, media)
    assert view["view_id"] in live["removals"] and live["ended"](view["view_id"])


# ------------------------------------------------------------------------------------------------ leakage tiles
@pytest.mark.parametrize(("role", "keys"), [("ceo", {"leakage"}), ("cfo", {"leakage"}), ("coo", {"open_findings"}),
                                            ("hr", {"idle_above_threshold"})])
def test_leakage_tiles_unavailable_until_first_scan(company, admin_sql, role, keys):
    co = company(roles=("cfo", "coo", "hr"))

    def board():
        admin_sql("DELETE FROM ems.dashboard_cache WHERE org_id = %s", co["org_id"])
        data = co[role].get(f"/api/v1/dashboards/{role}").json()["data"]
        return {t["key"] for t in data["tiles"]}, {u["key"]: u["reason"] for u in data["unavailable"]}
    tiles, unavailable = board()
    assert not keys & tiles and keys <= set(unavailable)
    assert all("leakage scan" in unavailable[k] for k in keys)
    admin_sql("UPDATE ems.organizations SET leakage_scanned_at = now() WHERE id = %s", co["org_id"])
    tiles, unavailable = board()
    assert keys <= tiles and not keys & set(unavailable)

