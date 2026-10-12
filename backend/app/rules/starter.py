"""Starter rules (spec Section 15). Seeded for every company when it is created (worker, `org.created`) and by the
nightly job for companies that predate them. A key that already exists in any version is never re-seeded, so a
company's own version of a starter rule always wins."""
import uuid

from app.platform.db import Db, jsonb
from app.rules import service

STARTER_RULES: dict[str, dict] = {
    "stale_deal_nudge": {
        "trigger": "deal.stale",
        "when": {"all": [{"fact": "deal.days_since_activity", "op": "gte", "value": 14},
                         {"any": [{"fact": "deal.stage", "op": "in", "value": ["proposal", "negotiation"]}]}]},
        "then": [{"action": "notify", "to": "owner", "template": "deal_stale"},
                 {"action": "create_task", "assign": "owner", "title": "Follow up: {deal.title}", "due_in_hours": 24}]},
    "overdue_billable_task": {
        "trigger": "task.overdue",
        "when": {"all": [{"fact": "task.billable", "op": "eq", "value": True}, {"fact": "task.hours_overdue", "op": "gte", "value": 24}]},
        "then": [{"action": "notify", "to": "project_owner", "template": "task_overdue"}]},
    "late_three_times": {
        "trigger": "attendance.late",
        "when": {"all": [{"fact": "employee.late_count_7d", "op": "gte", "value": 3}]},
        "then": [{"action": "notify", "to": "hr", "template": "late_three_times"}]},
    "invoice_overdue_at_risk": {
        "trigger": "invoice.overdue",
        "when": {"all": [{"fact": "invoice.days_overdue", "op": "gte", "value": 30}]},
        "then": [{"action": "set_stage_flag", "flag": "at_risk"}]},
    "leave_team_overlap": {
        "trigger": "leave.requested",
        "when": {"all": [{"fact": "team.on_leave_count", "op": "gte", "value": 2}]},
        "then": [{"action": "escalate", "to": "ceo", "template": "leave_team_overlap"}]},
    "prospect_high_score": {
        "trigger": "prospect.scored",
        "when": {"all": [{"fact": "prospect.score", "op": "gte", "value": 80}]},
        "then": [{"action": "notify", "to": "hunt_owner", "template": "prospect_high_score"}]},
}
# The approver is already notified of every leave request by the notification handler (worker/handlers.py), so the
# leave starter rule only adds the escalation part of Section 15.

for _defn in STARTER_RULES.values():
    service.validate(_defn)                                    # a broken starter rule fails at import, not at runtime


def seed(db: Db, org_id: uuid.UUID) -> int:
    """Insert missing starter rules (version 1) authored by the CEO. Returns how many were added."""
    ceo = db.scalar("SELECT user_id FROM ems.memberships WHERE role = 'ceo' AND status = 'active'")
    if ceo is None:
        return 0
    existing = {r["key"] for r in db.all("SELECT DISTINCT key FROM ems.rules")}
    added = 0
    for key, defn in STARTER_RULES.items():
        if key not in existing:
            db.execute("INSERT INTO ems.rules (id, org_id, key, version, trigger, definition, created_by) "
                       "VALUES (:id, :org, :k, 1, :t, CAST(:d AS jsonb), :u) ON CONFLICT (org_id, key, version) DO NOTHING",
                       id=uuid.uuid4(), org=org_id, k=key, t=defn["trigger"], d=jsonb(defn), u=ceo)
            added += 1
    return added
