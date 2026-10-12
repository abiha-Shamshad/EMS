"""HR Agent and policies (API-035..037), Lead Hunter (API-055..060), rule engine (API-061..064) and revenue leakage
(API-065/066), with the worker jobs behind them: crawl, rule runs, nightly leakage run (TASK-008, TASK-012, TASK-013)."""
import datetime as dt
import http.server
import threading
from zoneinfo import ZoneInfo

import pytest
from conftest import assert_contract, unique

from app.hunter import crawler
from app.hunter.crawler import Page
from worker import automation

PKT = ZoneInfo("Asia/Karachi")


def _today() -> dt.date:
    return dt.datetime.now(PKT).date()


def nightly(co, admin_sql, drain) -> None:
    """What the worker does at 01:00 company time."""
    admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (gen_random_uuid(), %s, 'platform.nightly', '{}')",
              co["org_id"])
    drain()


# ------------------------------------------------------------------------------------------------ HR policies + agent
def test_policies_are_versioned_and_apply_their_rules(company, admin_sql):
    co = company(roles=("hr", "manager", "employee"))
    hr, mgr = co["hr"], co["manager"]
    body = {"expected_version": 0, "text": "18 annual days and 8 casual days per year.", "rules": {"annual_days": 18, "casual_days": 8}}
    assert_contract("API-037", mgr.put("/api/v1/hr-agent/policies/leave", body), expect_status=403)       # team scope only
    v1 = assert_contract("API-037", hr.put("/api/v1/hr-agent/policies/leave", body), expect_status=200)
    assert v1["version"] == 1
    stale = hr.put("/api/v1/hr-agent/policies/leave", body)
    assert_contract("API-037", stale, expect_status=409)
    assert stale.json()["error"]["details"] == {"current_version": 1}
    bad = hr.put("/api/v1/hr-agent/policies/leave", {**body, "expected_version": 1, "rules": {"late_grace_minutes": 5}})
    assert bad.status_code == 400 and "rules.late_grace_minutes" in bad.json()["error"]["details"]["fields"]
    assert hr.put("/api/v1/hr-agent/policies/unknown", body).status_code == 400

    att = {"expected_version": 0, "text": "Work hours 09:00-18:00, 15 minutes grace.", "rules": {"late_grace_minutes": 15,
                                                                                                "daily_break_allowance_minutes": 50}}
    assert hr.put("/api/v1/hr-agent/policies/attendance", att).status_code == 200
    assert admin_sql("SELECT work_hours->>'late_grace_minutes', daily_break_allowance_minutes FROM ems.organizations WHERE id = %s",
                     co["org_id"])[0] == ("15", 50)
    hr.put("/api/v1/hr-agent/policies/monitoring", {"expected_version": 0, "text": "We see presence and the current task only."})
    assert admin_sql("SELECT room_policy_version FROM ems.organizations WHERE id = %s", co["org_id"])[0][0] == 2   # fresh consent

    items = assert_contract("API-036", co["employee"].get("/api/v1/hr-agent/policies"), expect_status=200)["items"]
    assert [(i["topic"], i["version"]) for i in items] == [("leave", 1), ("attendance", 1), ("monitoring", 1)]


def test_hr_agent_answers_from_records_and_never_guesses(company, admin_sql):
    co = company(roles=("hr", "manager", "employee"))
    hr, emp = co["hr"], co["employee"]
    admin_sql("INSERT INTO ems.leave_requests (id, org_id, user_id, kind, period, status) "
              "VALUES (gen_random_uuid(), %s, %s, 'annual', daterange(%s, %s, '[]'), 'approved')",
              co["org_id"], co["manager"].user_id, _today(), _today())
    who = assert_contract("API-035", hr.post("/api/v1/hr-agent/ask", {"question": "Who is on leave today?"}), expect_status=200)
    assert who["intent"] == "who_on_leave" and who["answered"] and "Usman Tariq (annual)" in who["text"] and len(who["sources"]) == 1

    denied = emp.post("/api/v1/hr-agent/ask", {"question": "Who is on leave today?"}).json()["data"]
    assert denied["answered"] is False and denied["data"] == []
    unknown = emp.post("/api/v1/hr-agent/ask", {"question": "What is the CEO's salary?"}).json()["data"]
    assert unknown == {"intent": "unknown", "answered": False, "text": unknown["text"], "data": [], "sources": []}
    assert "Who is on leave today?" in unknown["text"]
    no_policy = emp.post("/api/v1/hr-agent/ask", {"question": "What is the leave policy?"}).json()["data"]
    assert no_policy["answered"] is False and "No leave policy" in no_policy["text"]
    hr.put("/api/v1/hr-agent/policies/leave", {"expected_version": 0, "text": "18 annual days per year.", "rules": {"annual_days": 18}})
    policy = emp.post("/api/v1/hr-agent/ask", {"question": "What is the leave policy?"}).json()["data"]
    assert policy["answered"] and policy["text"] == "Leave policy (v1): 18 annual days per year."
    mine = emp.post("/api/v1/hr-agent/ask", {"question": "Give me my work summary"}).json()["data"]
    assert mine["intent"] == "work_summary" and mine["answered"] and "No work session" in mine["text"]
    other = emp.post("/api/v1/hr-agent/ask", {"question": "Work summary for Hina"}).json()["data"]
    assert other["answered"] is False                                        # an employee sees only their own summary
    assert_contract("API-035", emp.post("/api/v1/hr-agent/ask", {"question": "hi"}), expect_status=400)
    logged = admin_sql("SELECT intent, answered FROM ems.agent_logs WHERE org_id = %s ORDER BY created_at", co["org_id"])
    assert ("who_on_leave", True) in logged and ("unknown", False) in logged    # intent only, never the question


# ------------------------------------------------------------------------------------------------ Lead Hunter
HOME = """<html><head><title>BrightPixel | Digital marketing agency</title></head><body>
<link href="/wp-content/themes/bp.css">We are a marketing agency in Lahore, Pakistan with 25 employees.
Write to info@brightpixel.example or john.smith@brightpixel.example, call +92 300 1234567.
<a href="/contact">Contact us</a></body></html>"""
SITES = {
    "https://brightpixel.example/robots.txt": Page(200, "User-agent: *\nDisallow: /careers\n"),
    "https://brightpixel.example/": Page(200, HOME),
    "https://brightpixel.example/about": Page(200, "<html><body>About our digital agency</body></html>"),
    "https://brightpixel.example/services": Page(404),
    "https://brightpixel.example/contact": Page(200, "<html><body>sales@brightpixel.example</body></html>"),
    "https://adsmiths.example/robots.txt": Page(503),
    "https://quietco.example/robots.txt": Page(404),
    "https://quietco.example/": Page(200, "<html><head><title>QuietCo</title></head><body>Accounting firm</body></html>"),
}


def _fake_fetch(calls):
    def fetch(url):
        calls.append(url)
        return SITES.get(url, Page(None))
    return fetch


@pytest.fixture
def hunt(company, worker_engine, drain):
    co = company(roles=("manager", "employee"))
    mgr = co["manager"]
    suppressed = f"blocked-{unique()}.example"
    mgr.post("/api/v1/suppressions", {"kind": "domain", "value": suppressed, "reason": "opt_out"})
    crm_domain = f"northwind-{unique()}.example"
    mgr.post("/api/v1/contacts", {"name": "Ali Raza", "email": f"ali@{crm_domain}", "source": "referral",
                                  "company": {"name": "Northwind", "domain": crm_domain}}, idem=True)
    body = {"name": "Lahore marketing agencies", "max_pages_per_domain": 5,
            "seeds": {"domains": ["brightpixel.example", "https://www.AdSmiths.example/x", "quietco.example", crm_domain, suppressed]},
            "icp": {"industry_keywords": ["marketing agency", "digital agency"], "countries": ["PK"], "tech": ["wordpress", "shopify"],
                    "min_team_size": 10}}
    started = assert_contract("API-055", mgr.post("/api/v1/hunts", body, idem=True), expect_status=202)
    assert started["status"] == "queued" and started["domains"] == 5
    calls = []
    while automation.crawl_next_hunt(worker_engine, fetch=_fake_fetch(calls), sleep=lambda s: None):
        pass
    drain()
    return {"co": co, "mgr": mgr, "hunt_id": started["hunt_id"], "calls": calls}


def test_hunt_respects_sources_robots_and_suppression(hunt, admin_sql):
    mgr, hunt_id = hunt["mgr"], hunt["hunt_id"]
    status = assert_contract("API-056", mgr.get(f"/api/v1/hunts/{hunt_id}"), expect_status=200)
    assert status["status"] == "completed"
    assert status["stats"] == {"domains": 5, "fetched_pages": 4, "robots_disallowed": 1, "unreachable": 1, "prospects": 2,
                               "already_in_crm": 1, "suppressed": 1}
    assert "https://brightpixel.example/careers" not in hunt["calls"]                       # disallowed by robots.txt
    assert not [c for c in hunt["calls"] if "adsmiths" in c and not c.endswith("robots.txt")]  # 503 robots: nothing crawled
    assert not [c for c in hunt["calls"] if "northwind" in c or "blocked-" in c]
    decisions = {r[0] for r in admin_sql("SELECT robots_decision FROM ems.crawl_log WHERE hunt_id = %s", hunt_id)}
    assert decisions == {"allowed", "disallowed", "unreachable_blocked"}

    items = assert_contract("API-057", mgr.get(f"/api/v1/hunts/{hunt_id}/prospects"), expect_status=200)["items"]
    top = items[0]
    assert top["domain"] == "brightpixel.example" and top["company_name"] == "BrightPixel" and top["score"] == 100
    assert top["public_emails"] == ["info@brightpixel.example", "sales@brightpixel.example"]    # role addresses only
    assert any("uses wordpress" in r for r in top["score_reasons"])
    stored = admin_sql("SELECT public_emails, signals::text FROM ems.prospects WHERE id = %s", top["id"])[0]
    assert "john.smith" not in str(stored) and "300 1234567" not in str(stored)
    assert [i["domain"] for i in mgr.get(f"/api/v1/hunts/{hunt_id}/prospects", params={"min_score": 80}).json()["data"]["items"]] == [
        "brightpixel.example"]
    titles = [n["title"] for n in mgr.get("/api/v1/notifications").json()["data"]["items"]]
    assert "BrightPixel scored 100 in the Lead Hunter" in titles                            # starter rule prospect_high_score
    assert hunt["co"]["employee"].get(f"/api/v1/hunts/{hunt_id}").status_code == 403


def test_blocked_sources_and_seed_limit(company):
    mgr = company(roles=("manager",))["manager"]
    icp = {"industry_keywords": ["agency"]}
    social = mgr.post("/api/v1/hunts", {"name": "x", "seeds": {"domains": ["acme.example", "www.linkedin.com"]}, "icp": icp}, idem=True)
    assert_contract("API-055", social, expect_status=422)
    assert social.json()["error"]["details"] == {"domain": "linkedin.com"}            # reported as normalized
    assert mgr.post("/api/v1/hunts", {"name": "x", "seeds": {"domains": ["google.com.pk"]}, "icp": icp}, idem=True).status_code == 422
    many = mgr.post("/api/v1/hunts", {"name": "x", "seeds": {"domains": [f"d{i}.example" for i in range(201)]}, "icp": icp}, idem=True)
    assert_contract("API-055", many, expect_status=400)


def test_promote_draft_and_suppress(hunt, admin_sql):
    mgr, hunt_id = hunt["mgr"], hunt["hunt_id"]
    items = mgr.get(f"/api/v1/hunts/{hunt_id}/prospects").json()["data"]["items"]
    bright, quiet = items[0], items[1]
    draft = assert_contract("API-059", mgr.post(f"/api/v1/prospects/{bright['id']}/outreach-draft",
                                                {"template": "intro_services", "sender_name": "Usman Tariq", "offer": "website maintenance"}),
                            expect_status=200)
    assert draft["subject"] == "Website maintenance for BrightPixel" and "WordPress" in draft["body"]
    assert draft["body"].endswith("we will not contact you again.") and draft["send_via"] == "copy_to_mail_client"

    first = assert_contract("API-058", mgr.post(f"/api/v1/prospects/{bright['id']}/promote", {}), expect_status=201)
    again = mgr.post(f"/api/v1/prospects/{bright['id']}/promote", {}).json()["data"]
    assert again["contact_id"] == first["contact_id"] and first["lifecycle_stage"] == "lead"
    assert admin_sql("SELECT source, email FROM ems.contacts WHERE id = %s", first["contact_id"])[0] == ("lead_hunter", "info@brightpixel.example")

    added = assert_contract("API-060", mgr.post("/api/v1/suppressions", {"kind": "domain", "value": "QuietCo.example", "reason": "opt_out"}),
                            expect_status=201)
    assert added == {"kind": "domain", "stored_as": "sha256", "prospects_suppressed": 1}
    repeat = mgr.post("/api/v1/suppressions", {"kind": "domain", "value": "quietco.example", "reason": "opt_out"}).json()["data"]
    assert repeat["prospects_suppressed"] == 0                                # idempotent per (kind, value)
    assert_contract("API-058", mgr.post(f"/api/v1/prospects/{quiet['id']}/promote", {}), expect_status=422)
    blocked = mgr.post(f"/api/v1/prospects/{quiet['id']}/outreach-draft", {"template": "follow_up", "sender_name": "U", "offer": "seo"})
    assert_contract("API-059", blocked, expect_status=422)
    assert_contract("API-060", mgr.post("/api/v1/suppressions", {"kind": "email", "value": "not-an-email", "reason": "manual"}),
                    expect_status=400)
    assert admin_sql("SELECT count(*) FROM ems.suppression_list WHERE org_id = %s AND kind = 'domain'", hunt["co"]["org_id"])[0][0] == 2


class _Site(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server API
        routes = {"/robots.txt": (503, "text/plain", b""), "/page": (200, "text/html", b"<html>ok</html>"),
                  "/big": (200, "text/html", b"x" * (crawler.MAX_PAGE_BYTES + 10)), "/file": (200, "application/pdf", b"%PDF")}
        status, ctype, body = routes.get(self.path, (404, "text/html", b""))
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


def test_http_fetch_limits():
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _Site)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base, fetch = f"http://127.0.0.1:{server.server_port}", crawler.http_fetch("EMS-LeadHunter/1.0")
    try:
        assert fetch(f"{base}/robots.txt") == Page(503)
        assert fetch(f"{base}/page") == Page(200, "<html>ok</html>")
        assert fetch(f"{base}/big") == Page(200)                     # over 2 MB: not parsed
        assert fetch(f"{base}/file") == Page(200)                    # HTML only
    finally:
        server.shutdown()
    assert fetch(f"{base}/page").status is None                      # unreachable


# ------------------------------------------------------------------------------------------------ rules
def _stale_deal(co, admin_sql, days=20) -> dict:
    mgr = co["manager"]
    contact = mgr.post("/api/v1/contacts", {"name": "Ali", "email": f"ali.{unique()}@contoso.example", "source": "referral",
                                            "company": {"name": "Contoso", "domain": f"contoso-{unique()}.example"}}, idem=True).json()["data"]
    deal = mgr.post("/api/v1/deals", {"contact_id": contact["id"], "title": "Contoso redesign", "amount": "5000.00", "currency": "USD",
                                      "expected_close": "2026-12-01"}, idem=True).json()["data"]
    admin_sql("UPDATE ems.deals SET stage = 'proposal', last_activity_at = now() - make_interval(days => %s) WHERE id = %s", days, deal["id"])
    return deal


def test_rules_dashboard_create_and_simulate(company, drain):
    co = company(roles=("cto", "manager"))
    drain()                                                          # org.created seeds the starter rules
    cto = co["cto"]
    listed = assert_contract("API-061", cto.get("/api/v1/rules"), expect_status=200)
    assert {r["key"] for r in listed["items"]} == {"stale_deal_nudge", "overdue_billable_task", "late_three_times",
                                                   "invoice_overdue_at_risk", "leave_team_overlap", "prospect_high_score"}
    assert listed["external_api_calls_7d"] == 0
    assert_contract("API-061", co["manager"].get("/api/v1/rules"), expect_status=403)

    defn = {"trigger": "deal.stale", "when": {"all": [{"fact": "deal.secret", "op": "eq", "value": 1}]},
            "then": [{"action": "notify", "to": "owner", "template": "deal_stale"}]}
    bad = cto.post("/api/v1/rules", {"key": "secret_rule", "definition": defn}, idem=True)
    assert_contract("API-062", bad, expect_status=400)
    assert bad.json()["error"]["details"] == {"reason": "FACT_NOT_ALLOWED:deal.secret"}
    defn["when"] = {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 7}]}
    defn["then"] = [{"action": "notify", "to": "hunt_owner", "template": "deal_stale"}]
    who = cto.post("/api/v1/rules", {"key": "secret_rule", "definition": defn}, idem=True)
    assert who.status_code == 400 and who.json()["error"]["details"]["reason"] == "RECIPIENT_NOT_ALLOWED:hunt_owner"

    v2 = {"trigger": "deal.stale", "when": {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 10}]},
          "then": [{"action": "create_task", "assign": "owner", "title": "Follow up: {deal.title}", "due_in_hours": 48}]}
    saved = assert_contract("API-062", cto.post("/api/v1/rules", {"key": "stale_deal_nudge", "definition": v2}, idem=True), expect_status=201)
    assert saved["version"] == 2
    keys = {r["key"]: r for r in cto.get("/api/v1/rules").json()["data"]["items"]}
    assert keys["stale_deal_nudge"]["version"] == 2 and keys["stale_deal_nudge"]["id"] == saved["id"]

    v1 = next(r["id"] for r in listed["items"] if r["key"] == "stale_deal_nudge")
    starter = assert_contract("API-063", cto.post(f"/api/v1/rules/{v1}/simulate", {"facts": {"deal.days_since_activity": 15,
                              "deal.stage": "proposal", "deal.title": "Website rebuild"}}), expect_status=200)
    assert starter["actions"][1]["title"] == "Follow up: Website rebuild"
    facts = {"deal.days_since_activity": 15, "deal.title": "Website rebuild"}
    sim = cto.post(f"/api/v1/rules/{saved['id']}/simulate", {"facts": facts}).json()["data"]
    assert sim["matched"] and sim["actions"][0]["title"] == "Follow up: Website rebuild"
    assert sim["trace"] == [{"fact": "deal.days_since_activity", "op": "gte", "value": 10, "actual": 15, "result": True}]
    assert cto.post(f"/api/v1/rules/{saved['id']}/simulate", {"facts": {}}).json()["data"]["matched"] is False
    assert_contract("API-063", cto.post("/api/v1/rules/00000000-0000-0000-0000-000000000001/simulate", {"facts": {}}), expect_status=404)


def test_stale_deal_rule_creates_one_task_even_when_replayed(company, admin_sql, drain):
    """TASK-013 done-when: the stale-deal rule creates one task for the fixture and a replayed event creates none."""
    co = company(roles=("cfo", "coo", "manager"))
    drain()
    deal = _stale_deal(co, admin_sql)
    nightly(co, admin_sql, drain)
    nightly(co, admin_sql, drain)                                     # second run the same day: deterministic event IDs
    tasks = admin_sql("SELECT t.title, t.assignee_id::text, p.name FROM ems.tasks t JOIN ems.projects p ON p.id = t.project_id "
                      "WHERE t.org_id = %s", co["org_id"])
    assert tasks == [("Follow up: Contoso redesign", co["manager"].user_id, "Automation follow-ups")]
    titles = [n["title"] for n in co["manager"].get("/api/v1/notifications").json()["data"]["items"]]
    assert "No activity on Contoso redesign for 20 days" in titles
    runs = assert_contract("API-064", co["coo"].get("/api/v1/rule-runs", params={"outcome": "matched"}), expect_status=200)["items"]
    assert [(r["rule"], r["event"], r["actions"]) for r in runs] == [("stale_deal_nudge", "deal.stale", ["notify", "create_task"])]
    assert_contract("API-064", co["manager"].get("/api/v1/rule-runs"), expect_status=403)
    assert deal["id"]


def test_late_three_times_and_loop_guard(company, admin_sql, drain):
    co = company(roles=("hr", "employee"))
    drain()
    emp, org = co["employee"].user_id, co["org_id"]
    days, d = [], _today()
    while len(days) < 3:                                              # the three most recent weekdays before today
        d -= dt.timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    if (_today() - days[-1]).days > 6:
        pytest.skip("fewer than three weekdays in the last 7 days")
    for day in days:
        late = dt.datetime.combine(day, dt.time(11, 0), tzinfo=PKT)
        admin_sql("INSERT INTO ems.work_sessions (id, org_id, user_id, started_at, ended_at, state) "
                  "VALUES (gen_random_uuid(), %s, %s, %s, %s, 'closed')", org, emp, late, late + dt.timedelta(hours=6))
    admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (gen_random_uuid(), %s, 'room.checked_in', "
              "jsonb_build_object('user_id', %s::text, 'minutes_late', 120))", org, emp)
    admin_sql("INSERT INTO ems.outbox_events (id, org_id, routing_key, payload) VALUES (gen_random_uuid(), %s, 'task.overdue', "
              "jsonb_build_object('task_id', gen_random_uuid()::text, 'chain_depth', 3, 'task.billable', true, 'task.hours_overdue', 30))", org)
    drain()
    titles = [n["title"] for n in co["hr"].get("/api/v1/notifications").json()["data"]["items"]]
    assert "Bilal Ahmed was late 3 times in the last 7 days" in titles
    outcomes = dict(admin_sql("SELECT r.key, x.outcome FROM ems.rule_runs x JOIN ems.rules r ON r.id = x.rule_id WHERE x.org_id = %s", org))
    assert outcomes == {"late_three_times": "matched", "overdue_billable_task": "skipped_loop"}


# ------------------------------------------------------------------------------------------------ leakage
def test_nightly_leakage_findings_and_resolution(company, admin_sql, drain):
    co = company(roles=("cfo", "coo", "manager", "employee"))
    cfo, coo, mgr = co["cfo"], co["coo"], co["manager"]
    _stale_deal(co, admin_sql)
    contact = mgr.post("/api/v1/contacts", {"name": "Sara", "email": f"s.{unique()}@fabrikam.example", "source": "referral",
                                            "company": {"name": "Fabrikam", "domain": f"fab-{unique()}.example"}}, idem=True).json()["data"]
    deal = mgr.post("/api/v1/deals", {"contact_id": contact["id"], "title": "Fabrikam site", "amount": "6000.00", "currency": "USD",
                                      "expected_close": "2026-10-01"}, idem=True).json()["data"]
    won = mgr.post(f"/api/v1/deals/{deal['id']}/win", {"expected_version": 1}, idem=True).json()["data"]
    number = f"INV-{unique()}"
    inv = cfo.post("/api/v1/invoices", {"client_id": won["client"]["id"], "number": number, "amount": "6000.00", "currency": "USD",
                                        "issued_on": "2026-09-01", "due_on": "2026-09-15"}, idem=True).json()["data"]
    before = co["ceo"].get("/api/v1/dashboards/ceo").json()["data"]
    assert "leakage" in {u["key"] for u in before["unavailable"]}

    nightly(co, admin_sql, drain)
    listed = assert_contract("API-065", cfo.get("/api/v1/leakage/findings"), expect_status=200)
    kinds = {i["kind"]: i for i in listed["items"]}
    assert kinds["stale_deal"]["amount_at_risk"] == "2500.00" and kinds["stale_deal"]["label"] == "Contoso redesign - no activity 20 days"
    assert kinds["overdue_invoice"]["amount_at_risk"] == "6000.00" and kinds["overdue_invoice"]["label"].startswith(f"{number} overdue")
    assert listed["totals"]["amount_at_risk"] == "8500.00" and listed["totals"]["currency"] == "USD" and listed["last_scan_at"]
    assert admin_sql("SELECT status FROM ems.clients WHERE id = %s", won["client"]["id"])[0][0] == "onboarding"   # < 30 days rule
    assert_contract("API-065", co["employee"].get("/api/v1/leakage/findings"), expect_status=403)
    admin_sql("DELETE FROM ems.dashboard_cache WHERE org_id = %s", co["org_id"])
    tile = next(t for t in co["ceo"].get("/api/v1/dashboards/ceo").json()["data"]["tiles"] if t["key"] == "leakage")
    assert tile["value"] == "8500.00"

    stale = kinds["stale_deal"]["id"]
    assert_contract("API-066", cfo.post(f"/api/v1/leakage/findings/{stale}/resolve", {"resolution": "dismissed"}), expect_status=400)
    assert coo.post(f"/api/v1/leakage/findings/{stale}/resolve", {"resolution": "resolved"}).status_code == 403
    done = assert_contract("API-066", cfo.post(f"/api/v1/leakage/findings/{stale}/resolve",
                                               {"resolution": "resolved", "note": "Called the client"}), expect_status=200)
    assert done["status"] == "resolved" and done["resolved_by"] == "Omar Siddiqui"
    assert_contract("API-066", cfo.post(f"/api/v1/leakage/findings/{stale}/resolve", {"resolution": "dismissed", "note": "x"}),
                    expect_status=409)

    cfo.post(f"/api/v1/invoices/{inv['id']}/payments", {"amount": "6000.00", "received_on": "2026-10-10", "method": "bank_transfer"}, idem=True)
    nightly(co, admin_sql, drain)                                     # paid: the overdue finding resolves on the next run
    assert cfo.get("/api/v1/leakage/findings", params={"kind": "overdue_invoice"}).json()["data"]["items"] == []
    auto = cfo.get("/api/v1/leakage/findings", params={"status": "resolved", "kind": "overdue_invoice"}).json()["data"]["items"]
    assert auto[0]["evidence"]["resolution_note"] == "Resolved automatically: no longer detected"
    assert len(cfo.get("/api/v1/leakage/findings", params={"status": "resolved", "kind": "stale_deal"}).json()["data"]["items"]) == 1
