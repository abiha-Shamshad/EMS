"""Revenue-leakage run (spec Section 17): nightly at 01:00 company time in the worker, using the detectors in
engine/leakage.py with their default thresholds (no per-company settings exist yet).

* New findings are inserted once per fingerprint (DB-12). When a detector reports a kind + record that already has an
  open finding under an older fingerprint (unbilled time is fingerprinted per day), the open finding is refreshed
  instead, so the list does not grow one row per night.
* Open findings no longer reported are resolved automatically ("paying an invoice or logging an activity resolves the
  matching finding on the next run"). Findings created by rules (fingerprint `rule:...`) are left to people.
* The run ends by setting organizations.leakage_scanned_at, which un-gates the leakage dashboard tiles.
"""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Any

from app.engine import leakage as engine
from app.hr import service as hr
from app.platform.db import Db, jsonb
from app.platform.timeutil import Calendar, utcnow

DETECTOR_KINDS = ("unbilled_time", "overdue_invoice", "stale_deal", "won_without_project", "won_without_invoice", "over_budget",
                  "idle_paid_time")


def detect(db: Db, cal: Calendar, base_currency: str, now: dt.datetime) -> list[dict[str, Any]]:
    today = cal.local_date(now)
    local = cal.local
    all_projects = {p["id"]: p for p in db.all(
        "SELECT id, client_id, status, billing_type, hourly_rate, budget_amount, coalesce(currency, :base) AS currency FROM ems.projects",
        base=base_currency)}
    projects = {pid: p for pid, p in all_projects.items() if p["status"] not in ("completed", "cancelled")}
    entries = [{**e, "date": local(e["started_at"]).date()} for e in db.all(
        "SELECT e.id, e.user_id, e.minutes, e.billable, e.invoice_id, e.started_at, t.project_id FROM ems.time_entries e "
        "JOIN ems.tasks t ON t.id = e.task_id")]
    invoices = db.all("SELECT id, client_id, number, amount, currency, status, due_on FROM ems.invoices")
    payments = db.all("SELECT invoice_id, amount FROM ems.payments")
    deals = db.all("SELECT id, stage, amount, currency, last_activity_at, won_at FROM ems.deals WHERE stage <> 'lost'")
    open_deals = [{**d, "last_activity_on": local(d["last_activity_at"]).date()} for d in deals if d["stage"] in engine.STAGE_PROBABILITY]
    won = [{**d, "won_on": local(d["won_at"]).date()} for d in deals if d["stage"] == "won"]
    clients = db.all("SELECT id, origin_deal_id FROM ems.clients")
    rates = {r["user_id"]: r["cost_rate"] for r in db.all("SELECT user_id, cost_rate FROM ems.memberships WHERE cost_rate IS NOT NULL")}

    yesterday = today - dt.timedelta(days=1)                       # the last complete working day
    members = [r["user_id"] for r in db.all("SELECT user_id FROM ems.memberships WHERE status = 'active'")]
    day_totals = {u: s["totals"] for u, s in hr.day_summaries(db, cal, members, yesterday, now).items()}

    return [*engine.unbilled_time(entries, projects, today), *engine.overdue_invoices(invoices, payments, today),
            *engine.stale_deals(open_deals, today), *engine.won_follow_through(won, clients, all_projects, invoices, today),
            *engine.over_budget(projects, entries, rates), *engine.idle_paid_time(day_totals, rates, yesterday, base_currency)]


def run(db: Db, org_id: uuid.UUID) -> dict[str, int]:
    org = db.one("SELECT time_zone, work_hours, base_currency FROM ems.organizations")
    cal, now = Calendar(org["time_zone"], org["work_hours"]), utcnow()
    found = detect(db, cal, org["base_currency"], now)
    created = refreshed = 0
    seen: set[tuple[str, str]] = set()
    for f in found:
        seen.add((f["kind"], str(f["entity_id"])))
        current = db.one("SELECT id, fingerprint FROM ems.leakage_findings WHERE status = 'open' AND kind = :k AND entity_id = :e "
                         "AND fingerprint NOT LIKE 'rule:%' FOR UPDATE", k=f["kind"], e=f["entity_id"])
        if current is not None:                                       # still open: refresh it (new day, new amount)
            if current["fingerprint"] != f["fingerprint"]:
                db.execute("UPDATE ems.leakage_findings SET amount_at_risk = :a, currency = :c, evidence = CAST(:ev AS jsonb) WHERE id = :id",
                           a=f["amount_at_risk"], c=f["currency"], ev=jsonb(f["evidence"]), id=current["id"])
                refreshed += 1
            continue
        inserted = db.scalar(
            "INSERT INTO ems.leakage_findings (id, org_id, kind, entity_type, entity_id, fingerprint, amount_at_risk, currency, evidence) "
            "VALUES (:id, :org, :k, :et, :e, :fp, :a, :c, CAST(:ev AS jsonb)) ON CONFLICT (org_id, fingerprint) DO NOTHING RETURNING 1",
            id=uuid.uuid4(), org=org_id, k=f["kind"], et=f["entity_type"], e=f["entity_id"], fp=f["fingerprint"],
            a=f["amount_at_risk"], c=f["currency"], ev=jsonb(f["evidence"]))
        created += 1 if inserted else 0
    resolved = 0
    for o in db.all("SELECT id, kind, entity_id FROM ems.leakage_findings WHERE status = 'open' AND kind = ANY(:kinds) "
                    "AND fingerprint NOT LIKE 'rule:%'", kinds=list(DETECTOR_KINDS)):
        if (o["kind"], str(o["entity_id"])) not in seen:
            db.execute("UPDATE ems.leakage_findings SET status = 'resolved', resolved_at = now(), "
                       "evidence = evidence || jsonb_build_object('resolution_note', 'Resolved automatically: no longer detected') "
                       "WHERE id = :id", id=o["id"])
            resolved += 1
    db.execute("UPDATE ems.organizations SET leakage_scanned_at = now()")
    return {"created": created, "refreshed": refreshed, "resolved": resolved}


def rule_events(db: Db, cal: Calendar) -> list[tuple[str, str, dict[str, Any]]]:
    """Nightly rule triggers (Section 15): deal.stale for idle open deals, invoice.overdue for unpaid invoices past due.
    Returns (routing_key, dedupe key, payload) for the caller to emit with deterministic IDs."""
    now = utcnow()
    today = cal.local_date(now)
    out = []
    for d in db.all("SELECT d.id, d.title, d.stage, d.amount, d.currency, d.owner_id, d.last_activity_at, m.role AS owner_role "
                    "FROM ems.deals d LEFT JOIN ems.memberships m ON m.user_id = d.owner_id WHERE d.stage NOT IN ('won','lost')"):
        idle = (today - cal.local_date(d["last_activity_at"])).days
        if idle >= 1:
            out.append(("deal.stale", f"{d['id']}:{today}", {
                "entity_type": "deal", "entity_id": str(d["id"]), "owner_id": str(d["owner_id"]),
                "deal.days_since_activity": idle, "deal.stage": d["stage"], "deal.amount": str(d["amount"]), "deal.owner_role": d["owner_role"],
                "deal.title": d["title"], "deal.currency": d["currency"]}))
    for i in db.all("SELECT i.id, i.number, i.client_id, i.currency, i.due_on, i.amount - coalesce(p.paid, 0) AS outstanding, "
                    "c.status AS client_status, "
                    "(SELECT pr.owner_id FROM ems.projects pr WHERE pr.id = i.project_id) AS project_owner_id FROM ems.invoices i "
                    "LEFT JOIN (SELECT invoice_id, sum(amount) AS paid FROM ems.payments GROUP BY invoice_id) p ON p.invoice_id = i.id "
                    "LEFT JOIN ems.clients c ON c.id = i.client_id WHERE i.status IN ('sent','partially_paid') AND i.due_on < :today",
                    today=today):
        if Decimal(i["outstanding"]) > 0:
            out.append(("invoice.overdue", f"{i['id']}:{today}", {
                "entity_type": "invoice", "entity_id": str(i["id"]), "client_id": str(i["client_id"]),
                "project_owner_id": str(i["project_owner_id"]) if i["project_owner_id"] else None,
                "invoice.days_overdue": (today - i["due_on"]).days, "invoice.outstanding": str(i["outstanding"]),
                "client.status": i["client_status"], "invoice.number": i["number"], "invoice.currency": i["currency"]}))
    return out
