"""Read-only lists the web app needs beyond the contract: deal cards, clients, invoices, hunts and break requests."""
from conftest import unique


def _won_deal(mgr) -> dict:
    contact = mgr.post("/api/v1/contacts", {"name": "Ali", "email": f"ali.{unique()}@nw.example", "source": "referral",
                                            "company": {"name": "Northwind", "domain": f"nw-{unique()}.example"}}, idem=True).json()["data"]
    deal = mgr.post("/api/v1/deals", {"contact_id": contact["id"], "title": "Website rebuild", "amount": "5000.00", "currency": "USD",
                                      "expected_close": "2026-12-01"}, idem=True).json()["data"]
    return {"contact": contact, "deal": deal}


def test_deal_cards_and_clients(company):
    co = company(roles=("manager", "cfo", "employee"))
    mgr = co["manager"]
    open_deal = _won_deal(mgr)
    won = _won_deal(mgr)
    win = mgr.post(f"/api/v1/deals/{won['deal']['id']}/win", {"expected_version": 1}, idem=True).json()["data"]

    cards = mgr.get("/api/v1/deals").json()["data"]["items"]
    assert {c["id"] for c in cards} == {open_deal["deal"]["id"], won["deal"]["id"]}
    card = next(c for c in cards if c["id"] == open_deal["deal"]["id"])
    assert card["stage"] == "new" and card["amount"] == "5000.00" and card["owner"]["name"] == "Usman Tariq"
    assert card["contact"]["name"] == "Ali" and card["company"] == "Northwind" and card["stale"] is False and card["version"] == 1
    assert [c["id"] for c in mgr.get("/api/v1/deals", params={"stage": "won"}).json()["data"]["items"]] == [won["deal"]["id"]]
    assert co["cfo"].get("/api/v1/deals").status_code == 200                       # CFO reads the CRM
    assert co["employee"].get("/api/v1/deals").status_code == 403

    clients = co["cfo"].get("/api/v1/clients").json()["data"]["items"]
    assert [(c["id"], c["name"], c["status"]) for c in clients] == [(win["client"]["id"], "Northwind", "onboarding")]
    assert co["employee"].get("/api/v1/clients").status_code == 403


def test_invoice_list_shows_outstanding(company):
    co = company(roles=("manager", "cfo"))
    mgr, cfo = co["manager"], co["cfo"]
    won = _won_deal(mgr)
    client = mgr.post(f"/api/v1/deals/{won['deal']['id']}/win", {"expected_version": 1}, idem=True).json()["data"]["client"]["id"]
    inv = cfo.post("/api/v1/invoices", {"client_id": client, "number": f"INV-{unique()}", "amount": "2500.00", "currency": "USD",
                                        "issued_on": "2026-10-05", "due_on": "2026-10-19"}, idem=True).json()["data"]
    cfo.post(f"/api/v1/invoices/{inv['id']}/payments", {"amount": "1000.00", "received_on": "2026-10-10", "method": "cash"}, idem=True)
    items = cfo.get("/api/v1/invoices").json()["data"]["items"]
    assert len(items) == 1 and items[0]["status"] == "partially_paid" and items[0]["client"] == "Northwind"
    assert (items[0]["amount"], items[0]["paid"], items[0]["outstanding"]) == ("2500.00", "1000.00", "1500.00")
    assert cfo.get("/api/v1/invoices", params={"status": "paid"}).json()["data"]["items"] == []
    assert mgr.get("/api/v1/invoices").status_code == 403


def test_hunt_list(company):
    co = company(roles=("manager", "employee"))
    mgr = co["manager"]
    mgr.post("/api/v1/hunts", {"name": "Agencies", "seeds": {"domains": ["acme.example"]}, "icp": {"industry_keywords": ["agency"]}}, idem=True)
    items = mgr.get("/api/v1/hunts").json()["data"]["items"]
    assert [(h["name"], h["status"], h["created_by"], h["stats"]["domains"]) for h in items] == [("Agencies", "queued", "Usman Tariq", 1)]
    assert co["employee"].get("/api/v1/hunts").status_code == 403


def test_break_requests_by_scope(company):
    co = company(roles=("manager", "employee", "hr"))
    emp, mgr = co["employee"], co["manager"]
    session = emp.post("/api/v1/room/check-in", {}).json()["data"]["session_id"]
    req = emp.post("/api/v1/room/breaks", {"session_id": session, "kind": "personal", "minutes": 90}).json()["data"]

    pending = mgr.get("/api/v1/room/breaks", params={"status": "requested"}).json()["data"]["items"]
    assert [(b["id"], b["name"], b["can_decide"]) for b in pending] == [(req["break_id"], "Bilal Ahmed", True)]
    own = emp.get("/api/v1/room/breaks").json()["data"]["items"]
    assert [(b["id"], b["can_decide"]) for b in own] == [(req["break_id"], False)]       # nobody decides their own break
    assert co["hr"].get("/api/v1/room/breaks").json()["data"]["items"][0]["can_decide"] is True
    assert emp.get("/api/v1/room/breaks", params={"from": "2026-01-01", "to": "2026-12-31"}).status_code == 400


def test_org_settings_read(company):
    co = company(roles=("employee",))
    org = co["employee"].get("/api/v1/org").json()["data"]
    assert org["name"] == "Acme Tech" and org["time_zone"] == "Asia/Karachi" and org["setup_state"] == "active"
    assert org["work_hours"]["start"] == "09:00" and org["version"] >= 1 and org["next_step"] == "done"
