"""Revenue-leakage detectors (proposed path: backend/app/engine/leakage.py). Pure functions over plain dicts.

Every finding has a deterministic fingerprint so repeated nightly runs do not duplicate it
(database: UNIQUE (org_id, fingerprint)). Amounts are estimates of money at risk, labelled as such in the UI.
"""
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

STAGE_PROBABILITY = {"new": Decimal("0.10"), "qualified": Decimal("0.25"), "proposal": Decimal("0.50"), "negotiation": Decimal("0.70")}
DEFAULTS = {"unbilled_after_days": 7, "stale_deal_days": 14, "won_project_grace_days": 3, "won_invoice_grace_days": 30,
            "budget_warning_ratio": Decimal("0.90"), "idle_minutes_threshold": 60}


def money(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def finding(kind, entity_type, entity_id, fp_suffix, amount, currency, evidence):
    return {"kind": kind, "entity_type": entity_type, "entity_id": entity_id,
            "fingerprint": f"{kind}:{entity_id}:{fp_suffix}",
            "amount_at_risk": None if amount is None else money(amount), "currency": currency, "evidence": evidence}


def unbilled_time(entries, projects, today: date, cfg=DEFAULTS):
    """Billable time on hourly client projects, older than N days, not on any invoice. One finding per project."""
    by_project: dict = {}
    for e in entries:
        p = projects.get(e["project_id"])
        if not p or p["billing_type"] != "hourly" or not e["billable"] or e.get("invoice_id"):
            continue
        if (today - e["date"]).days < cfg["unbilled_after_days"]:
            continue
        by_project.setdefault(p["id"], []).append(e)
    out = []
    for pid, es in sorted(by_project.items()):
        p = projects[pid]
        minutes = sum(e["minutes"] for e in es)
        out.append(finding("unbilled_time", "project", pid, today.isoformat(), Decimal(minutes) / 60 * Decimal(p["hourly_rate"]),
                           p["currency"], {"minutes": minutes, "entries": len(es), "oldest": min(e["date"] for e in es).isoformat()}))
    return out


def overdue_invoices(invoices, payments, today: date):
    paid: dict = {}
    for pay in payments:
        paid[pay["invoice_id"]] = paid.get(pay["invoice_id"], Decimal(0)) + Decimal(pay["amount"])
    out = []
    for inv in invoices:
        if inv["status"] not in ("sent", "partially_paid") or inv["due_on"] >= today:
            continue
        outstanding = Decimal(inv["amount"]) - paid.get(inv["id"], Decimal(0))
        if outstanding <= 0:
            continue
        out.append(finding("overdue_invoice", "invoice", inv["id"], inv["due_on"].isoformat(), outstanding, inv["currency"],
                           {"number": inv["number"], "days_overdue": (today - inv["due_on"]).days}))
    return out


def stale_deals(deals, today: date, cfg=DEFAULTS):
    out = []
    for d in deals:
        if d["stage"] not in STAGE_PROBABILITY:
            continue
        idle = (today - d["last_activity_on"]).days
        if idle < cfg["stale_deal_days"]:
            continue
        out.append(finding("stale_deal", "deal", d["id"], d["last_activity_on"].isoformat(),
                           Decimal(d["amount"]) * STAGE_PROBABILITY[d["stage"]], d["currency"],
                           {"stage": d["stage"], "days_without_activity": idle, "weighting": str(STAGE_PROBABILITY[d["stage"]])}))
    return out


def won_follow_through(deals, clients, projects, invoices, today: date, cfg=DEFAULTS):
    """Won deals that never became a project, or whose project has no invoice after the grace period."""
    out = []
    client_by_deal = {c["origin_deal_id"]: c for c in clients}
    for d in deals:
        if d["stage"] != "won":
            continue
        age = (today - d["won_on"]).days
        c = client_by_deal.get(d["id"])
        client_projects = [p for p in projects.values() if c and p.get("client_id") == c["id"]]
        if age >= cfg["won_project_grace_days"] and not client_projects:
            out.append(finding("won_without_project", "deal", d["id"], "v1", d["amount"], d["currency"], {"days_since_won": age}))
        elif age >= cfg["won_invoice_grace_days"] and c and not any(i["client_id"] == c["id"] for i in invoices):
            out.append(finding("won_without_invoice", "deal", d["id"], "v1", d["amount"], d["currency"], {"days_since_won": age}))
    return out


def over_budget(projects, entries, cost_rates, cfg=DEFAULTS):
    """Fixed-price projects whose internal cost reached the warning ratio of the budget."""
    out = []
    for p in projects.values():
        if p["billing_type"] != "fixed" or not p.get("budget_amount"):
            continue
        cost = sum(Decimal(e["minutes"]) / 60 * Decimal(cost_rates.get(e["user_id"], 0)) for e in entries if e["project_id"] == p["id"])
        budget = Decimal(p["budget_amount"])
        if cost >= budget * cfg["budget_warning_ratio"]:
            out.append(finding("over_budget", "project", p["id"], f"{int(cost // (budget / 10))}", max(cost - budget, Decimal(0)), p["currency"],
                               {"cost_to_date": str(money(cost)), "budget": str(money(budget)), "ratio": str((cost / budget).quantize(Decimal('0.01')))}))
    return out


def idle_paid_time(day_totals, cost_rates, day: date, currency, cfg=DEFAULTS):
    """Idle minutes inside open work sessions above the threshold. Review signal for HR, not an automatic penalty."""
    out = []
    for user_id, t in sorted(day_totals.items()):
        idle = t.get("idle", 0)
        if idle <= cfg["idle_minutes_threshold"]:
            continue
        out.append(finding("idle_paid_time", "employee", user_id, day.isoformat(), Decimal(idle) / 60 * Decimal(cost_rates.get(user_id, 0)), currency,
                           {"idle_minutes": idle, "active_minutes": t.get("active", 0), "note": "estimate; review with the employee before any action"}))
    return out
