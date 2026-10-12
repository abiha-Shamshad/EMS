"""Per-role access (TASK-005), worker and scheduler (TASK-006), dashboards (API-067) and notifications (API-069/070)."""
import datetime as dt
import uuid

import pytest
from conftest import assert_contract

from worker import jobs
from worker.main import OutboxLoop
from worker.registry import HANDLERS

ROLES = ("ceo", "cto", "cfo", "coo", "hr", "manager", "employee")
# (method, path, body, roles that are allowed). "Allowed" means anything but 403.
ROUTES = [
    ("GET", "/api/v1/room/live", None, {"ceo", "coo"}),
    ("GET", "/api/v1/employees", None, {"ceo", "coo", "hr", "manager"}),
    ("GET", "/api/v1/hr/reports/daily", None, {"ceo", "coo", "hr", "manager"}),
    ("POST", "/api/v1/projects", {"name": "Internal", "billing_type": "internal"}, {"ceo", "cto", "coo", "manager"}),
    ("POST", "/api/v1/contacts/search", {}, {"ceo", "coo", "manager", "cfo"}),
    ("POST", "/api/v1/invoices", {"client_id": str(uuid.uuid4()), "number": "INV-1", "amount": "1.00", "currency": "USD",
                                  "issued_on": "2026-10-01", "due_on": "2026-10-02"}, {"ceo", "cfo"}),
    ("PATCH", "/api/v1/org", {"expected_version": 999}, {"ceo", "hr"}),
    ("GET", "/api/v1/dashboards/ceo", None, {"ceo"}),
    ("GET", "/api/v1/dashboards/employee", None, {"ceo", "manager", "employee"}),
    ("GET", "/api/v1/room/my-viewers", None, set(ROLES)),
]


@pytest.mark.parametrize("role", ROLES)
def test_role_matrix(company, role):
    co = company()
    api = co[role]
    for method, path, body, allowed in ROUTES:
        r = api.call(method, path, body, idem=method == "POST")
        if role in allowed:
            assert r.status_code != 403, f"{role} should reach {method} {path}: {r.text}"
        else:
            assert r.status_code == 403 and r.json()["error"]["code"] == "AUTHORIZATION_DENIED", f"{role} must not reach {method} {path}"


def test_invitation_notifies_within_one_worker_pass(company, drain):
    """TASK-006 done-when: member.invited produces a notification (the worker polls every second)."""
    co = company(roles=("hr",))
    co["ceo"].post("/api/v1/invitations", {"invites": [{"email": f"n.{co['tag']}@acme.example", "role": "employee"}]}, idem=True)
    drain()
    items = assert_contract("API-069", co["hr"].get("/api/v1/notifications"), expect_status=200)["items"]
    note = next(i for i in items if i["kind"] == "member.invited")
    assert note["read"] is False
    unread = co["hr"].get("/api/v1/notifications").json()["data"]["unread"]
    assert_contract("API-070", co["hr"].post(f"/api/v1/notifications/{note['id']}/read"), expect_status=200)
    assert co["hr"].post(f"/api/v1/notifications/{note['id']}/read").status_code == 200          # idempotent
    assert co["hr"].get("/api/v1/notifications", params={"unread_only": True}).json()["data"]["unread"] == unread - 1
    assert_contract("API-070", co["ceo"].post(f"/api/v1/notifications/{note['id']}/read"), expect_status=404)   # not the owner


def test_failing_handler_is_retried_then_skipped(company, worker_engine, admin_sql):
    co = company(roles=())
    admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (gen_random_uuid(), %s, 'test.poison', '{}')",
              co["org_id"])
    calls = []

    def boom(db, event):
        calls.append(event.id)
        raise RuntimeError("handler bug")
    HANDLERS["test.poison"] = [boom]
    try:
        loop = OutboxLoop(worker_engine)
        loop.run_once()
        loop.run_once()                                           # back-off: not retried immediately
        assert len(calls) == 1
        event_id = calls[0]
        assert admin_sql("SELECT attempts, next_attempt_at > now(), dead FROM ems.outbox_events WHERE id = %s", event_id)[0] == (1, True, False)
        admin_sql("UPDATE ems.outbox_events SET attempts = 9, next_attempt_at = now() WHERE id = %s", event_id)
        loop.run_once()                                           # 10th failure: marked dead, stays unpublished
        loop.run_once()
        assert len(calls) == 2
        assert admin_sql("SELECT published_at, dead FROM ems.outbox_events WHERE id = %s", event_id)[0] == (None, True)
    finally:
        HANDLERS.pop("test.poison")
        admin_sql("UPDATE ems.outbox_events SET published_at = now() WHERE routing_key = 'test.poison'")


def test_minute_tick_offline_auto_close_and_view_sweep(company, worker_engine, admin_sql, monkeypatch):
    co = company(roles=("coo", "employee"))
    emp = co["employee"]
    session = emp.post("/api/v1/room/check-in", {}).json()["data"]["session_id"]
    admin_sql("UPDATE ems.work_sessions SET started_at = now() - interval '2 days', last_heartbeat_at = now() - interval '2 days' "
              "WHERE id = %s", session)
    admin_sql("INSERT INTO ems.stream_views (id, org_id, viewer_id, subject_user_id, reason, started_at) "
              "VALUES (gen_random_uuid(), %s, %s, %s, 'Old view', now() - interval '1 hour')", co["org_id"], co["coo"].user_id, emp.user_id)
    jobs.tick(worker_engine)
    state, presence = admin_sql("SELECT state, presence FROM ems.work_sessions WHERE id = %s", session)[0]
    assert state == "auto_closed" and presence == "offline"
    assert admin_sql("SELECT count(*) FROM ems.extension_tokens WHERE session_id = %s AND revoked_at IS NULL", session)[0][0] == 0
    assert admin_sql("SELECT count(*) FROM ems.stream_views WHERE org_id = %s AND ended_at IS NULL", co["org_id"])[0][0] == 0
    # Ended when the viewer was removed (LiveKit is not configured here, so there is no participant to remove).
    assert admin_sql("SELECT ended_at >= started_at + interval '15 minutes' FROM ems.stream_views WHERE org_id = %s", co["org_id"])[0][0]


def test_daily_events_are_emitted_once(company, worker_engine, admin_sql, monkeypatch):
    co = company(roles=())
    at_2330 = dt.datetime(2026, 10, 12, 18, 31, tzinfo=dt.UTC)      # 23:31 Asia/Karachi
    monkeypatch.setattr(jobs, "utcnow", lambda: at_2330)
    jobs.tick(worker_engine)
    jobs.tick(worker_engine)
    rows = admin_sql("SELECT count(*) FROM ems.outbox_events WHERE org_id = %s AND routing_key = 'platform.hr_daily_report'", co["org_id"])
    assert rows[0][0] == 1


@pytest.mark.parametrize("role", ["ceo", "cto", "cfo", "coo", "hr", "employee"])
def test_dashboards_show_only_sourced_tiles(company, role):
    co = company(roles=("cto", "cfo", "coo", "hr", "employee"))
    r = co["ceo"].get(f"/api/v1/dashboards/{role}")
    if role == "cfo":                                               # the contract example is the CFO variant
        data = assert_contract("API-067", r, expect_status=200)
    else:
        assert r.status_code == 200, r.text
        data = r.json()["data"]
        assert {"role", "period", "currency", "tiles", "unavailable"} <= set(data)
    assert data["role"] == role and data["tiles"]
    assert all(t["source"] for t in data["tiles"])
    if role in ("ceo", "cto", "cfo", "coo", "hr"):
        assert data["unavailable"] and all(u["reason"] for u in data["unavailable"])
    if role == "cfo":
        assert {"operating_expenses", "net_profit"} <= {u["key"] for u in data["unavailable"]}
    if role == "cto":
        assert {"system_uptime", "open_incidents", "deployments", "latency"} <= {u["key"] for u in data["unavailable"]}
    if role != "ceo":
        own = co[role].get(f"/api/v1/dashboards/{role}")
        assert own.status_code == 200
        assert co[role].get("/api/v1/dashboards/ceo").status_code == 403
