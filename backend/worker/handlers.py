"""Notification and graph-memory handlers for domain events (spec Sections 16, 31.2; TASK-006, TASK-014)."""
import uuid
from typing import Any

from app.graph import service as graph
from app.hr import service as hr
from app.platform import events
from app.platform.db import Db
from worker.registry import Event, handles


def _uid(value: Any) -> uuid.UUID | None:
    return uuid.UUID(value) if value else None


def _name(db: Db, user_id: Any) -> str:
    return db.scalar("SELECT name FROM ems.users WHERE id = :u", u=user_id) or "Former member"


def _role_holders(db: Db, *roles: str) -> list[uuid.UUID]:
    return [r["user_id"] for r in db.all("SELECT user_id FROM ems.memberships WHERE status = 'active' AND role = ANY(:r)", r=list(roles))]


def person_node(db: Db, org_id: uuid.UUID, user_id: Any) -> uuid.UUID:
    return graph.ensure_node(db, org_id, "person", user_id, _name(db, user_id))


# ------------------------------------------------------------------------------------------------ members
@handles("member.invited")
def notify_invitation(db: Db, e: Event) -> None:
    actor = _uid(e.payload.get("actor_id"))
    recipients = [u for u in _role_holders(db, "ceo", "hr") if u != actor]
    events.notify(db, e.org_id, recipients, e.routing_key, f"{_name(db, actor)} invited a new {e.payload.get('role', 'member')}",
                  "invitation", _uid(e.payload.get("invitation_id")))


@handles("member.joined")
def member_joined(db: Db, e: Event) -> None:
    user_id = _uid(e.payload["user_id"])
    recipients = [_uid(e.payload.get("invited_by")), *_role_holders(db, "ceo")]
    events.notify(db, e.org_id, [u for u in recipients if u and u != user_id], e.routing_key,
                  f"{_name(db, user_id)} joined as {e.payload.get('role')}", "membership", user_id)
    person_node(db, e.org_id, user_id)


@handles("member.role_changed")
def member_structure(db: Db, e: Event) -> None:
    person = person_node(db, e.org_id, e.payload["user_id"])
    manager_id = _uid(e.payload.get("manager_id"))
    manager = person_node(db, e.org_id, manager_id) if manager_id else None
    graph.relink(db, e.org_id, person, "reports_to", manager, "manager set")
    graph.relink_incoming(db, e.org_id, person, "manages", manager, "manager set")


@handles("member.deactivated")
def member_deactivated(db: Db, e: Event) -> None:
    """Close the person's current edges (history is kept); ownership moved to `reassign_to` is re-linked."""
    person = person_node(db, e.org_id, e.payload["user_id"])
    db.execute("UPDATE ems.graph_edges SET valid_to = now() WHERE valid_to IS NULL AND (src = :p OR dst = :p) "
               "AND kind IN ('reports_to','manages','works_on','owns')", p=person)
    successor = _uid(e.payload.get("reassign_to"))
    if successor:
        owner = person_node(db, e.org_id, successor)
        for kind, table in (("deal", "deals"), ("project", "projects")):
            for row in db.all(f"SELECT n.id FROM ems.graph_nodes n JOIN ems.{table} x ON x.id = n.ref_id "  # noqa: S608 - fixed tables
                              "WHERE n.kind = :k AND x.owner_id = :o", k=kind, o=successor):
                graph.relink_incoming(db, e.org_id, row["id"], "owns", owner, "reassigned on deactivation")


# ------------------------------------------------------------------------------------------------ room
@handles("room.break_requested")
def break_requested(db: Db, e: Event) -> None:
    if not e.payload.get("needs_approval"):
        return
    user_id = _uid(e.payload["user_id"])
    approver = hr.approver_for(db, user_id)
    events.notify(db, e.org_id, approver["user_ids"], e.routing_key,
                  f"{_name(db, user_id)} asks for a {e.payload.get('minutes')}-minute {e.payload.get('kind')} break", "break",
                  _uid(e.payload.get("break_id")))


@handles("room.break_decided")
def break_decided(db: Db, e: Event) -> None:
    events.notify(db, e.org_id, [_uid(e.payload["user_id"])], e.routing_key, f"Your break request was {e.payload.get('decision')}",
                  "break", _uid(e.payload.get("break_id")))


# ------------------------------------------------------------------------------------------------ leave
@handles("leave.requested")
def leave_requested(db: Db, e: Event) -> None:
    user_id = _uid(e.payload["user_id"])
    approver = hr.approver_for(db, user_id)
    events.notify(db, e.org_id, approver["user_ids"], e.routing_key,
                  f"{_name(db, user_id)} requested {e.payload.get('days')} day(s) {e.payload.get('kind')} leave", "leave_request",
                  _uid(e.payload.get("request_id")))


@handles("leave.decided")
def leave_decided(db: Db, e: Event) -> None:
    note = e.payload.get("note")
    title = f"Your leave request was {e.payload.get('decision')}" + (f": {note}" if note else "")
    events.notify(db, e.org_id, [_uid(e.payload["user_id"])], e.routing_key, title, "leave_request", _uid(e.payload.get("request_id")))


# ------------------------------------------------------------------------------------------------ graph memory (Section 16)
def _client_node(db: Db, org_id: uuid.UUID, client_id: Any) -> uuid.UUID | None:
    label = db.scalar("SELECT co.name FROM ems.clients c JOIN ems.companies co ON co.id = c.company_id WHERE c.id = :c", c=client_id)
    return graph.ensure_node(db, org_id, "client", client_id, label) if label else None


def _project_edges(db: Db, org_id: uuid.UUID, project_id: Any) -> uuid.UUID | None:
    p = db.one("SELECT id, name, client_id, owner_id FROM ems.projects WHERE id = :p", p=project_id)
    if p is None:
        return None
    node = graph.ensure_node(db, org_id, "project", p["id"], p["name"])
    graph.relink_incoming(db, org_id, node, "owns", person_node(db, org_id, p["owner_id"]), "project owner")
    if p["client_id"]:
        client = _client_node(db, org_id, p["client_id"])
        if client:
            graph.link(db, org_id, node, client, "billed_by", "project client")
    return node


@handles("project.created")
def project_created(db: Db, e: Event) -> None:
    _project_edges(db, e.org_id, e.payload["project_id"])


@handles("task.created", "task.updated")
def task_assignment(db: Db, e: Event) -> None:
    assignee = _uid(e.payload.get("assignee_id"))
    if assignee is None:
        return
    project = _project_edges(db, e.org_id, e.payload["project_id"])
    if project:
        graph.link(db, e.org_id, person_node(db, e.org_id, assignee), project, "works_on", "task assigned")


@handles("contact.created")
def contact_created(db: Db, e: Event) -> None:
    c = db.one("SELECT c.id, c.name, c.company_id, co.name AS company FROM ems.contacts c LEFT JOIN ems.companies co ON co.id = c.company_id "
               "WHERE c.id = :c", c=e.payload["contact_id"])
    if c is None:
        return
    node = graph.ensure_node(db, e.org_id, "contact", c["id"], c["name"])
    if c["company_id"]:
        graph.link(db, e.org_id, node, graph.ensure_node(db, e.org_id, "company", c["company_id"], c["company"]), "belongs_to", "contact saved")


@handles("deal.created")
def deal_created(db: Db, e: Event) -> None:
    d = db.one("SELECT id, title, owner_id FROM ems.deals WHERE id = :d", d=e.payload["deal_id"])
    if d:
        node = graph.ensure_node(db, e.org_id, "deal", d["id"], d["title"])
        graph.relink_incoming(db, e.org_id, node, "owns", person_node(db, e.org_id, d["owner_id"]), "deal owner")


@handles("deal.won")
def deal_won(db: Db, e: Event) -> None:
    d = db.one("SELECT id, title, owner_id, contact_id FROM ems.deals WHERE id = :d", d=e.payload["deal_id"])
    if d is None:
        return
    deal = graph.ensure_node(db, e.org_id, "deal", d["id"], d["title"])
    graph.relink_incoming(db, e.org_id, deal, "owns", person_node(db, e.org_id, d["owner_id"]), "deal owner")
    client = _client_node(db, e.org_id, e.payload["client_id"])
    contact_name = db.scalar("SELECT name FROM ems.contacts WHERE id = :c", c=d["contact_id"])
    contact = graph.ensure_node(db, e.org_id, "contact", d["contact_id"], contact_name)
    if client:
        graph.link(db, e.org_id, contact, client, "contact_of", "deal won")
        graph.link(db, e.org_id, client, deal, "originated_from", "deal won")
    project = _project_edges(db, e.org_id, e.payload["project_id"])
    if project:
        graph.link(db, e.org_id, project, deal, "originated_from", "deal won")


@handles("invoice.recorded")
def invoice_recorded(db: Db, e: Event) -> None:
    inv = db.one("SELECT id, number, client_id FROM ems.invoices WHERE id = :i", i=e.payload["invoice_id"])
    if inv:
        client = _client_node(db, e.org_id, inv["client_id"])
        if client:
            graph.link(db, e.org_id, graph.ensure_node(db, e.org_id, "invoice", inv["id"], inv["number"]), client, "billed_by", "invoice saved")
