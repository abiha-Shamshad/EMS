"""People/HR (TASK-008 without the HR Agent) and projects, tasks, time (TASK-009)."""
import datetime as dt

from conftest import assert_contract


def _next_monday() -> dt.date:
    d = dt.date.today() + dt.timedelta(days=7)
    return d - dt.timedelta(days=d.weekday())


def test_leave_request_overlap_balance_and_decision(company, admin_sql, drain):
    co = company(roles=("hr", "manager", "employee"))
    emp, mgr, hr = co["employee"], co["manager"], co["hr"]
    admin_sql("INSERT INTO ems.hr_policies (org_id, topic, version, text, rules, published_by) VALUES "
              "(%s, 'leave', 1, '18 annual days and 8 casual days per year.', '{\"annual_days\": 18, \"casual_days\": 8}', %s)",
              co["org_id"], co["ceo"].user_id)
    mon = _next_monday()
    body = {"kind": "annual", "start_date": mon.isoformat(), "end_date": (mon + dt.timedelta(days=2)).isoformat(), "reason": "Family event"}
    created = assert_contract("API-031", emp.post("/api/v1/leave-requests", body, idem=True), expect_status=201)
    assert created["days"] == 3 and created["approver"] == "Usman Tariq" and created["balance_after_approval"] == {"annual": 15}
    overlap = emp.post("/api/v1/leave-requests", {**body, "start_date": (mon + dt.timedelta(days=1)).isoformat()}, idem=True)
    assert_contract("API-031", overlap, expect_status=409)
    weekend = emp.post("/api/v1/leave-requests", {"kind": "casual", "start_date": (mon - dt.timedelta(days=2)).isoformat(),
                                                  "end_date": (mon - dt.timedelta(days=1)).isoformat()}, idem=True)
    assert weekend.status_code == 400                                       # no working days
    too_many = emp.post("/api/v1/leave-requests", {"kind": "casual", "start_date": (mon + dt.timedelta(days=7)).isoformat(),
                                                   "end_date": (mon + dt.timedelta(days=20)).isoformat()}, idem=True)
    assert_contract("API-031", too_many, expect_status=422)

    queue = assert_contract("API-032", mgr.get("/api/v1/leave-requests", params={"scope": "to_decide"}), expect_status=200)
    assert [i["request_id"] for i in queue["items"]] == [created["request_id"]]
    drain()
    assert any("requested 3 day(s) annual leave" in n["title"] for n in mgr.get("/api/v1/notifications").json()["data"]["items"])
    own = emp.post(f"/api/v1/leave-requests/{created['request_id']}/decision", {"expected_version": 1, "decision": "approved"})
    assert own.status_code == 403
    decided = assert_contract("API-033", mgr.post(f"/api/v1/leave-requests/{created['request_id']}/decision",
                                                  {"expected_version": 1, "decision": "approved", "note": "Enjoy"}), expect_status=200)
    assert decided["status"] == "approved" and decided["decided_by"] == "Usman Tariq"
    second = hr.post(f"/api/v1/leave-requests/{created['request_id']}/decision", {"expected_version": 2, "decision": "rejected"})
    assert second.status_code == 409 and second.json()["error"]["details"]["current_status"] == "approved"
    drain()
    assert emp.get("/api/v1/notifications").json()["data"]["items"][0]["title"] == "Your leave request was approved: Enjoy"


def test_directory_attendance_and_report(company):
    co = company(roles=("hr", "manager", "employee"))
    emp, mgr, hr = co["employee"], co["manager"], co["hr"]
    emp.post("/api/v1/room/check-in", {})
    directory = assert_contract("API-029", hr.get("/api/v1/employees"), expect_status=200)
    bilal = next(i for i in directory["items"] if i["user_id"] == emp.user_id)
    assert bilal["today"]["state"] == "checked_in" and bilal["manager"] == "Usman Tariq" and bilal["leave_balance_days"] is None
    team = mgr.get("/api/v1/employees").json()["data"]["items"]
    assert [i["user_id"] for i in team] == [emp.user_id]                    # manager: team only
    assert_contract("API-029", emp.get("/api/v1/employees"), expect_status=403)
    att = assert_contract("API-030", emp.get("/api/v1/attendance"), expect_status=200)
    assert att["days"][0]["status"] == "present" and att["totals"]["present_days"] == 1
    assert emp.get("/api/v1/attendance", params={"user_id": mgr.user_id}).status_code == 403
    too_long = hr.get("/api/v1/attendance", params={"user_id": emp.user_id, "from": "2026-01-01", "to": "2026-06-01"})
    assert_contract("API-030", too_long, expect_status=400)
    report = assert_contract("API-034", hr.get("/api/v1/hr/reports/daily"), expect_status=200)
    assert report["headcount"] == 4 and report["present"] == 1
    week = hr.get("/api/v1/hr/reports/daily", params={"week": "2026-W42"})
    assert week.status_code == 200 and "days" in week.json()["data"]
    assert_contract("API-034", emp.get("/api/v1/hr/reports/daily"), expect_status=403)


def test_projects_board_moves_and_time(company):
    co = company(roles=("manager", "employee", "cfo"))
    mgr, emp = co["manager"], co["employee"]
    bad = mgr.post("/api/v1/projects", {"name": "Contoso support", "billing_type": "hourly"}, idem=True)
    assert_contract("API-039", bad, expect_status=400)
    assert_contract("API-039", emp.post("/api/v1/projects", {"name": "x", "billing_type": "internal"}, idem=True), expect_status=403)
    project = assert_contract("API-039", mgr.post("/api/v1/projects", {"name": "Platform", "billing_type": "internal"}, idem=True),
                              expect_status=201)
    pid = project["id"]
    nobody = mgr.post(f"/api/v1/projects/{pid}/tasks", {"title": "x", "assignee_id": co["org_id"]}, idem=True)
    assert_contract("API-041", nobody, expect_status=422)
    task = assert_contract("API-041", mgr.post(f"/api/v1/projects/{pid}/tasks", {"title": "Auth API", "assignee_id": emp.user_id,
                                                "due_at": "2026-10-12T13:00:00Z", "estimate_minutes": 480}, idem=True), expect_status=201)
    tid = task["id"]
    edited = assert_contract("API-042", emp.patch(f"/api/v1/tasks/{tid}", {"expected_version": 1, "due_at": "2026-10-13T13:00:00Z"}),
                             expect_status=200)
    assert edited["version"] == 2
    stale = emp.patch(f"/api/v1/tasks/{tid}", {"expected_version": 1, "title": "x"})
    assert_contract("API-042", stale, expect_status=409)
    jump = emp.post(f"/api/v1/tasks/{tid}/move", {"expected_version": 2, "to_status": "done", "position": 1})
    assert_contract("API-043", jump, expect_status=422)
    assert jump.json()["error"]["details"]["allowed"] == ["active"]
    moved = assert_contract("API-043", emp.post(f"/api/v1/tasks/{tid}/move", {"expected_version": 2, "to_status": "active", "position": 1}),
                            expect_status=200)
    assert moved["status"] == "active"
    board = assert_contract("API-040", emp.get(f"/api/v1/projects/{pid}/board"), expect_status=200)
    assert board["columns"]["active"][0]["title"] == "Auth API" and board["project"]["status"] == "active"
    assert_contract("API-040", co["cfo"].get(f"/api/v1/projects/{pid}/board"), expect_status=404)   # not a member
    listed = assert_contract("API-038", emp.get("/api/v1/projects"), expect_status=200)
    assert [p["id"] for p in listed["items"]] == [pid]

    session = emp.post("/api/v1/room/check-in", {}).json()["data"]
    started = session["started_at"]
    overlap = emp.post(f"/api/v1/tasks/{tid}/time-entries", {"started_at": started, "minutes": 1}, idem=True)
    assert_contract("API-044", overlap, expect_status=409)
    yesterday = (dt.datetime.now(dt.UTC) - dt.timedelta(days=1)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    logged = assert_contract("API-044", emp.post(f"/api/v1/tasks/{tid}/time-entries",
                                                 {"started_at": yesterday, "minutes": 60, "note": "Client call"}, idem=True), expect_status=201)
    assert logged["source"] == "manual" and logged["billable"] is True
    future = emp.post(f"/api/v1/tasks/{tid}/time-entries", {"started_at": "2099-01-01T00:00:00Z", "minutes": 5}, idem=True)
    assert future.status_code == 400
