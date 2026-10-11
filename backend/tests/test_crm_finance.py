"""CRM and client lifecycle, invoices and payments (TASK-010), graph memory (TASK-014), TEST-006 Win and payment parts."""
import threading
import uuid

from conftest import Api, assert_contract, unique


def _contact(mgr, company=True, email=None) -> dict:
    body = {"name": "Ali Raza", "email": email or f"ali.{unique()}@northwind.example", "phone": "+923001234567", "source": "referral"}
    if company:
        body["company"] = {"name": "Northwind Digital", "domain": f"northwind-{unique()}.example"}
    return assert_contract("API-045", mgr.post("/api/v1/contacts", body, idem=True), expect_status=201)


def _deal(mgr, contact_id, amount="5000.00", currency="USD") -> dict:
    return assert_contract("API-048", mgr.post("/api/v1/deals", {"contact_id": contact_id, "title": "Website rebuild", "amount": amount,
                                                                 "currency": currency, "expected_close": "2026-10-10"}, idem=True),
                           expect_status=201)


def test_contacts_search_details_and_suppression(company, admin_sql):
    co = company(roles=("manager", "cfo", "employee"))
    mgr = co["manager"]
    c = _contact(mgr, email=f"ali.{co['tag']}@northwind.example")
    assert c["lifecycle_stage"] == "lead" and c["owner"] == "Usman Tariq"
    dup = mgr.post("/api/v1/contacts", {"name": "Ali", "email": f"ali.{co['tag']}@northwind.example"}, idem=True)
    assert dup.status_code == 200 and dup.json()["data"]["already_exists"] is True
    admin_sql("INSERT INTO ems.suppression_list (org_id, kind, value_hash, reason) VALUES (%s, 'domain', sha256('optout.example'), 'opt_out')",
              co["org_id"])
    blocked = mgr.post("/api/v1/contacts", {"name": "No", "email": "info@optout.example"}, idem=True)
    assert_contract("API-045", blocked, expect_status=422)
    found = assert_contract("API-046", co["cfo"].post("/api/v1/contacts/search", {"query": "northwind"}), expect_status=200)
    assert [i["id"] for i in found["items"]] == [c["id"]]
    assert co["cfo"].post("/api/v1/contacts/search", {"query": "n"}).status_code == 400
    assert co["employee"].post("/api/v1/contacts/search", {}).status_code == 403
    details = assert_contract("API-047", mgr.get(f"/api/v1/contacts/{c['id']}"), expect_status=200)
    assert details["company"]["name"] == "Northwind Digital"


def test_pipeline_stages_and_currency(company):
    co = company(roles=("manager",))
    mgr = co["manager"]
    c = _contact(mgr)
    d = _deal(mgr, c["id"])
    _deal(mgr, c["id"], amount="1000.00")
    moved = assert_contract("API-050", mgr.post(f"/api/v1/deals/{d['id']}/stage", {"expected_version": 1, "to_stage": "proposal"}),
                            expect_status=200)
    assert moved["version"] == 2
    assert_contract("API-050", mgr.post(f"/api/v1/deals/{d['id']}/stage", {"expected_version": 2, "to_stage": "won"}), expect_status=422)
    lost = mgr.post(f"/api/v1/deals/{d['id']}/stage", {"expected_version": 2, "to_stage": "lost"})
    assert lost.json()["error"]["code"] == "LOST_REASON_REQUIRED"
    pipe = assert_contract("API-049", mgr.get("/api/v1/deals/pipeline"), expect_status=200)
    assert pipe["weighted_open"] == "2600.00"                          # 5000 x 0.50 + 1000 x 0.10
    _deal(mgr, c["id"], amount="100000.00", currency="PKR")
    assert_contract("API-049", mgr.get("/api/v1/deals/pipeline"), expect_status=400)
    assert mgr.get("/api/v1/deals/pipeline", params={"currency": "PKR"}).json()["data"]["stages"][0]["amount"] == "100000.00"


def test_win_is_one_transaction_and_replay_safe(company, drain):
    co = company(roles=("manager", "cfo"))
    mgr = co["manager"]
    no_company = _contact(mgr, company=False)
    lonely = _deal(mgr, no_company["id"])
    assert_contract("API-051", mgr.post(f"/api/v1/deals/{lonely['id']}/win", {"expected_version": 1}, idem=True), expect_status=422)

    c = _contact(mgr)
    d = _deal(mgr, c["id"])
    body = {"expected_version": 1, "project": {"name": "Northwind website", "billing_type": "fixed", "budget_amount": "5000.00",
                                               "template": "website_standard"}, "renewal_date": "2027-10-10"}
    key = uuid.uuid4().hex
    won = assert_contract("API-051", mgr.post(f"/api/v1/deals/{d['id']}/win", body, idem=key), expect_status=200)
    assert won["project"]["tasks_created"] == 12 and won["client"]["status"] == "onboarding"
    replay = mgr.post(f"/api/v1/deals/{d['id']}/win", body, idem=key)
    assert replay.status_code == 200 and replay.json()["data"]["client"]["id"] == won["client"]["id"]
    again = mgr.post(f"/api/v1/deals/{d['id']}/win", body, idem=True)
    assert again.status_code == 409 and again.json()["error"]["details"]["client_id"] == won["client"]["id"]
    assert mgr.get(f"/api/v1/contacts/{c['id']}").json()["data"]["lifecycle_stage"] == "customer"

    drain()                                                             # graph edges are written by the worker
    related = mgr.get(f"/api/v1/contacts/{c['id']}").json()["data"]["related"]
    assert {"client", "project", "deal"} <= {r["kind"] for r in related}
    graph = assert_contract("API-068", mgr.get("/api/v1/graph/neighbors", params={"kind": "project", "ref_id": won["project"]["id"],
                                                                                   "depth": 2}), expect_status=200)
    assert any(n["kind"] == "client" and n["label"] == "Northwind Digital" for n in graph["neighbors"])
    assert mgr.get("/api/v1/graph/neighbors", params={"kind": "project", "ref_id": won["project"]["id"], "depth": 4}).status_code == 400


def test_concurrent_wins_create_one_client(company, admin_sql):
    """TEST-006 Win part: 20 parallel wins of one deal (different keys) give exactly one client."""
    co = company(roles=("manager",))
    mgr = co["manager"]
    d = _deal(mgr, _contact(mgr)["id"])
    codes = []

    def go():
        codes.append(mgr.post(f"/api/v1/deals/{d['id']}/win", {"expected_version": 1}, idem=True).status_code)
    threads = [threading.Thread(target=go) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [200] + [409] * 19
    assert admin_sql("SELECT count(*) FROM ems.clients WHERE origin_deal_id = %s", d["id"])[0][0] == 1


def test_invoices_payments_and_activity(company, admin_sql):
    co = company(roles=("manager", "cfo"))
    mgr, cfo = co["manager"], co["cfo"]
    d = _deal(mgr, _contact(mgr)["id"])
    won = mgr.post(f"/api/v1/deals/{d['id']}/win", {"expected_version": 1}, idem=True).json()["data"]
    act = assert_contract("API-052", mgr.post("/api/v1/activities", {"entity_type": "deal", "entity_id": d["id"], "kind": "call",
                                                                     "note": "Agreed payment terms", "occurred_at": "2026-10-02T05:30:00Z"},
                                              idem=True), expect_status=201)
    assert act["entity_id"] == d["id"]
    future = mgr.post("/api/v1/activities", {"entity_type": "deal", "entity_id": d["id"], "kind": "call", "occurred_at": "2099-01-01T00:00:00Z"},
                      idem=True)
    assert_contract("API-052", future, expect_status=400)

    number = f"INV-{unique()}"
    inv_body = {"client_id": won["client"]["id"], "project_id": won["project"]["id"], "number": number, "amount": "2500.00",
                "currency": "USD", "issued_on": "2026-10-05", "due_on": "2026-10-19", "time_entry_ids": []}
    assert_contract("API-053", mgr.post("/api/v1/invoices", inv_body, idem=True), expect_status=403)
    inv = assert_contract("API-053", cfo.post("/api/v1/invoices", inv_body, idem=True), expect_status=201)
    assert inv["outstanding"] == "2500.00"
    assert_contract("API-053", cfo.post("/api/v1/invoices", inv_body, idem=True), expect_status=409)
    assert cfo.post("/api/v1/invoices", {**inv_body, "number": f"INV-{unique()}", "due_on": "2026-10-01"}, idem=True).status_code == 400

    codes = []

    def pay():
        codes.append(cfo.post(f"/api/v1/invoices/{inv['id']}/payments", {"amount": "1000.00", "received_on": "2026-10-18",
                                                                        "method": "bank_transfer"}, idem=True).status_code)
    threads = [threading.Thread(target=pay) for _ in range(5)]          # TEST-006 payment part: never overpaid
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(codes) == [201, 201, 422, 422, 422]
    last = assert_contract("API-054", cfo.post(f"/api/v1/invoices/{inv['id']}/payments", {"amount": "500.00", "received_on": "2026-10-18",
                                                                                         "method": "cash"}, idem=True), expect_status=201)
    assert last == {"payment_id": last["payment_id"], "invoice_status": "paid", "outstanding": "0.00"}
    over = cfo.post(f"/api/v1/invoices/{inv['id']}/payments", {"amount": "0.01", "received_on": "2026-10-18", "method": "cash"}, idem=True)
    assert_contract("API-054", over, expect_status=422)
    assert admin_sql("SELECT sum(amount) FROM ems.payments WHERE invoice_id = %s", inv["id"])[0][0] == 2500


def test_money_must_be_a_decimal_string(company):
    co = company(roles=("manager",))
    r = co["manager"].post("/api/v1/deals", {"contact_id": str(uuid.uuid4()), "title": "x", "amount": 5000.5, "currency": "USD"}, idem=True)
    assert r.status_code == 400 and "amount" in r.json()["error"]["details"]["fields"]


def test_crm_is_closed_to_employees(company, app):
    co = company(roles=("employee",))
    emp = co["employee"]
    assert emp.post("/api/v1/contacts", {"name": "x"}, idem=True).status_code == 403
    assert emp.get("/api/v1/deals/pipeline").status_code == 403
    assert Api(app).get("/api/v1/deals/pipeline").status_code == 401
