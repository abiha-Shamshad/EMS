"""Request pipeline, auth and onboarding, members and roles (TASK-003, TASK-004, TASK-005, TEST-007)."""
import uuid

from conftest import PASSWORD, Api, assert_contract, set_member, unique


def test_health_outside_envelope(app):
    r = Api(app).get("/health")
    body = assert_contract("API-001", r)
    assert body["status"] in ("ready", "degraded") and body["version"] == "1.0.0"
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["referrer-policy"] == "same-origin"


def test_signup_me_and_setup(company):
    co = company(roles=())
    ceo = co["ceo"]
    me = assert_contract("API-009", ceo.get("/api/v1/me"), expect_status=200)
    assert me["active_org"]["role"] == "ceo" and me["dashboard"] == "ceo" and "dashboards.all" in me["permissions"]
    r = ceo.patch("/api/v1/org", {"expected_version": 1, "industry": "Software services", "size_band": "11-50",
                                  "work_hours": {"days": ["mon", "tue", "wed", "thu", "fri"], "start": "09:00", "end": "18:00",
                                                 "late_grace_minutes": 10}})
    data = assert_contract("API-010", r, expect_status=200)
    assert data["version"] == 2 and data["next_step"] == "invite_team"
    stale = ceo.patch("/api/v1/org", {"expected_version": 1, "industry": "x"})
    assert stale.status_code == 409 and stale.json()["error"]["details"] == {"current_version": 2}
    skip = ceo.patch("/api/v1/org", {"expected_version": 2, "setup_state": "active"})
    assert skip.json()["data"]["setup_state"] == "active"


def test_signup_conflicts_and_validation(app, company):
    co = company(roles=())
    other = Api(app)
    base = {"company_name": "Other", "company_slug": f"other-{unique()}", "country": "PK", "time_zone": "Asia/Karachi",
            "name": "X", "email": co["emails"]["ceo"], "password": PASSWORD}
    assert other.post("/api/v1/auth/signup", base, idem=True).json()["error"]["code"] == "EMAIL_IN_USE"
    weak = other.post("/api/v1/auth/signup", {**base, "email": f"n.{unique()}@x.example", "password": "short"}, idem=True)
    assert weak.status_code == 400 and weak.json()["error"]["code"] == "VALIDATION_FAILED"
    no_key = other.post("/api/v1/auth/signup", {**base, "email": f"n.{unique()}@x.example"})
    assert no_key.status_code == 400
    tz = other.post("/api/v1/auth/signup", {**base, "email": f"n.{unique()}@x.example", "time_zone": "Mars/Base"}, idem=True)
    assert tz.status_code == 400


def test_login_logout_and_rate_limit(app, company):
    co = company(roles=())
    email = co["emails"]["ceo"]
    b = Api(app)
    wrong = b.post("/api/v1/auth/login", {"email": email, "password": "not-the-password!"})
    assert_contract("API-003", wrong, expect_status=401)
    unknown = b.post("/api/v1/auth/login", {"email": f"nobody.{unique()}@x.example", "password": "whatever-password"})
    assert unknown.json()["error"] == wrong.json()["error"]            # no account enumeration
    ok = b.post("/api/v1/auth/login", {"email": email, "password": PASSWORD, "remember": True})
    data = assert_contract("API-003", ok, expect_status=200)
    assert data["redirect"] == "/dashboards/ceo" and len(data["organizations"]) == 1
    assert "max-age" in ok.headers["set-cookie"].lower() and "httponly" in ok.headers["set-cookie"].lower()
    assert_contract("API-004", b.post("/api/v1/auth/logout"), expect_status=200)
    assert b.get("/api/v1/me").status_code == 401                      # revoked immediately (DB-04)
    c = Api(app)
    codes = [c.post("/api/v1/auth/login", {"email": email, "password": "wrong-password-1"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429
    limited = c.post("/api/v1/auth/login", {"email": email, "password": PASSWORD})
    assert limited.status_code == 429 and int(limited.headers["retry-after"]) >= 1


def test_csrf_required_for_unsafe_methods(company):
    ceo = company(roles=())["ceo"]
    r = ceo.client.patch("/api/v1/org", json={"expected_version": 1, "industry": "x"})   # no X-CSRF-Token
    assert r.status_code == 403 and r.json()["error"]["code"] == "AUTHORIZATION_DENIED"


def test_no_fake_integrations(app, company):
    """TEST-007: copy links instead of email; Google returns 503; reset says delivery is not configured."""
    co = company(roles=())
    r = co["ceo"].post("/api/v1/invitations", {"invites": [{"email": f"a.{unique()}@acme.example", "role": "employee"}]}, idem=True)
    data = assert_contract("API-011", r, expect_status=201)
    assert data["email_delivery"] == "not_configured" and data["copy_links"] is True and data["results"][0]["invite_link"]
    g = Api(app).get("/api/v1/auth/google/start")
    assert_contract("API-007", g, expect_status=503)
    assert g.json()["error"]["code"] == "GOOGLE_NOT_CONFIGURED"
    f = Api(app).post("/api/v1/auth/password/forgot", {"email": co["emails"]["ceo"]})
    assert_contract("API-005", f, expect_status=202)
    assert f.json()["data"]["email_delivery"] == "not_configured"
    reset = Api(app).post("/api/v1/auth/password/reset", {"token": "rst_not_a_real_token", "new_password": "a-new-long-passphrase-2026"})
    assert_contract("API-006", reset, expect_status=410)


def test_invitations_idempotency_and_acceptance(app, company):
    co = company(roles=())
    ceo, tag = co["ceo"], unique()
    body = {"invites": [{"email": f"bilal.{tag}@acme.example", "role": "employee"}, {"email": f"x.{tag}@acme.example", "role": "ceo"}]}
    bad = ceo.post("/api/v1/invitations", body, idem=True)
    assert bad.status_code == 400 and "invites[1].role" in bad.json()["error"]["details"]["fields"]
    body["invites"].pop()
    key = uuid.uuid4().hex
    first = ceo.post("/api/v1/invitations", body, idem=key)
    replay = ceo.post("/api/v1/invitations", body, idem=key)
    assert replay.status_code == 201 and replay.json()["data"] == first.json()["data"]
    assert ceo.post("/api/v1/invitations", {"invites": [{"email": "z@acme.example", "role": "hr"}]}, idem=key).json()["error"]["code"] \
        == "IDEMPOTENCY_KEY_REUSED"
    again = ceo.post("/api/v1/invitations", body, idem=True).json()["data"]["results"][0]
    assert again["status"] == "already_invited"
    token = first.json()["data"]["results"][0]["invite_link"].split("token=")[1]

    stranger = Api(app)
    signup = stranger.post("/api/v1/auth/signup", {"company_name": "Elsewhere", "company_slug": f"else-{tag}", "country": "PK",
                                                   "time_zone": "Asia/Karachi", "name": "S", "email": f"s.{tag}@x.example",
                                                   "password": PASSWORD}, idem=True)
    assert signup.status_code == 201
    assert_contract("API-012", stranger.post("/api/v1/invitations/accept", {"token": token}), expect_status=403)

    bilal = Api(app)
    joined = bilal.post("/api/v1/invitations/accept", {"token": token, "name": "Bilal Ahmed", "password": PASSWORD})
    data = assert_contract("API-012", joined, expect_status=200)
    assert data["membership"]["role"] == "employee" and data["next_step"] == "install_extension"
    reuse = Api(app).post("/api/v1/invitations/accept", {"token": token, "name": "B", "password": PASSWORD})
    assert reuse.status_code == 410 and reuse.json()["error"]["code"] == "INVITATION_INVALID"


def test_members_roles_and_deactivation(company, admin_sql):
    co = company()
    ceo, cfo, hr = co["ceo"], co["cfo"], co["hr"]
    listed = assert_contract("API-013", ceo.get("/api/v1/members"), expect_status=200)
    assert all("cost_rate" in m for m in listed["items"])
    assert all("cost_rate" not in m for m in hr.get("/api/v1/members").json()["data"]["items"])     # finance only
    emp = co["employee"].user_id
    promoted = set_member(co, emp, role="manager")
    assert promoted["role"] == "manager"
    ceo_row = next(m for m in ceo.get("/api/v1/members").json()["data"]["items"] if m["role"] == "ceo")
    r = hr.patch(f"/api/v1/members/{co['ceo'].user_id}", {"expected_version": ceo_row["version"], "role": "coo"})
    assert_contract("API-014", r, expect_status=422)
    rate = cfo.patch(f"/api/v1/members/{emp}", {"expected_version": promoted["version"], "cost_rate": "12.50"})
    assert rate.status_code == 200 and rate.json()["data"]["cost_rate"] == "12.50"
    assert cfo.patch(f"/api/v1/members/{emp}", {"expected_version": promoted["version"] + 1, "title": "x"}).status_code == 403
    matrix = assert_contract("API-016", co["employee"].get("/api/v1/roles/permissions"), expect_status=200)
    assert matrix["matrix"]["room.view_live"] == ["ceo", "coo"] and matrix["team_scope"]["leave.decide"] == ["manager"]

    assert_contract("API-015", hr.post(f"/api/v1/members/{co['ceo'].user_id}/deactivate", {}, idem=True), expect_status=422)
    co["employee"].post("/api/v1/room/check-in", {})
    done = hr.post(f"/api/v1/members/{emp}/deactivate", {"reassign_to": co["manager"].user_id, "reason": "Contract ended"}, idem=True)
    data = assert_contract("API-015", done, expect_status=200)
    assert data["status"] == "deactivated" and data["work_session_closed"] is True
    gone = co["employee"].get("/api/v1/me")
    assert gone.status_code == 423 and gone.json()["error"]["code"] == "MEMBER_DEACTIVATED"


def test_tenant_isolation(company):
    """TASK-003 done-when: company A's session cannot read company B's members or records."""
    a, b = company(roles=("employee",)), company(roles=("employee",), name="Other Co")
    a_ids = {m["user_id"] for m in a["ceo"].get("/api/v1/members").json()["data"]["items"]}
    b_ids = {m["user_id"] for m in b["ceo"].get("/api/v1/members").json()["data"]["items"]}
    assert a_ids.isdisjoint(b_ids) and len(a_ids) == 2
    foreign = a["ceo"].get("/api/v1/members", headers={"X-Org-Id": b["org_id"]})
    assert foreign.status_code == 403
    project = b["ceo"].post("/api/v1/projects", {"name": "B internal", "billing_type": "internal"}, idem=True).json()["data"]["id"]
    assert a["ceo"].get(f"/api/v1/projects/{project}/board").status_code == 404
    assert a["ceo"].patch(f"/api/v1/members/{b['employee'].user_id}", {"expected_version": 1, "title": "x"}).status_code == 404
