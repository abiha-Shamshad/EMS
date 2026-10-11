"""Projects, tasks and time shared logic (spec Section 12), also used by the Win action (API-051)."""
import uuid
from decimal import Decimal
from typing import Any

from app.platform.context import Ctx
from app.platform.db import Db
from app.platform.errors import ApiError, not_found
from app.projects.templates import TEMPLATES

# Board moves (Section 12): todo<->active, active<->review, review->done, done->review.
TRANSITIONS = {"todo": {"active"}, "active": {"todo", "review"}, "review": {"active", "done"}, "done": {"review"}}
PROJECT_COLUMNS = "id, client_id, name, status, billing_type, budget_amount, hourly_rate, currency, owner_id, version"


def is_member(db: Db, project: dict, user_id: uuid.UUID) -> bool:
    return project["owner_id"] == user_id or bool(
        db.scalar("SELECT 1 FROM ems.tasks WHERE project_id = :p AND assignee_id = :u LIMIT 1", p=project["id"], u=user_id))


def project_for(ctx: Ctx, project_id: uuid.UUID, lock: bool = False) -> dict[str, Any]:
    """The project if the caller may see it; otherwise NOT_FOUND (no hint that it exists)."""
    project = ctx.db.one(f"SELECT {PROJECT_COLUMNS} FROM ems.projects WHERE id = :p"  # noqa: S608 - constant columns
                         + (" FOR UPDATE" if lock else ""), p=project_id)
    if project is None or not (ctx.can("projects.manage") or is_member(ctx.db, project, ctx.user_id)):
        raise not_found("Project")
    return project


def require_active_member(db: Db, user_id: uuid.UUID | None, what: str = "assignee") -> None:
    if user_id is not None and not db.scalar("SELECT 1 FROM ems.memberships WHERE user_id = :u AND status = 'active'", u=user_id):
        raise ApiError("ASSIGNEE_NOT_MEMBER", f"The {what} is not an active member of this company.")


def cost_to_date(db: Db, project_ids: list[uuid.UUID]) -> dict[uuid.UUID, dict[str, Any]]:
    """Internal cost = minutes / 60 x member cost rate. `rates_missing` counts entries whose member has no cost rate,
    so a budget ratio is never presented as complete when it is not."""
    if not project_ids:
        return {}
    rows = db.all("SELECT t.project_id, coalesce(sum(e.minutes * m.cost_rate / 60.0), 0) AS cost, "
                  "count(*) FILTER (WHERE m.cost_rate IS NULL) AS rates_missing "
                  "FROM ems.time_entries e JOIN ems.tasks t ON t.id = e.task_id JOIN ems.memberships m ON m.user_id = e.user_id "
                  "WHERE t.project_id = ANY(:ids) GROUP BY t.project_id", ids=project_ids)
    return {r["project_id"]: {"cost": Decimal(r["cost"]), "rates_missing": r["rates_missing"]} for r in rows}


def insert_project(ctx: Ctx, *, name: str, client_id: uuid.UUID | None, billing_type: str, budget_amount: Decimal | None,
                   hourly_rate: Decimal | None, currency: str | None, owner_id: uuid.UUID) -> uuid.UUID:
    project_id = uuid.uuid4()
    ctx.db.execute("INSERT INTO ems.projects (id, org_id, client_id, name, billing_type, budget_amount, hourly_rate, currency, owner_id) "
                   "VALUES (:id, :org, :c, :n, :b, :budget, :rate, :cur, :owner)",
                   id=project_id, org=ctx.org_id, c=client_id, n=name, b=billing_type, budget=budget_amount, rate=hourly_rate,
                   cur=currency, owner=owner_id)
    return project_id


def insert_task(ctx: Ctx, project_id: uuid.UUID, title: str, *, assignee_id: uuid.UUID | None = None, due_at=None,
                estimate_minutes: int | None = None, billable: bool = True) -> dict[str, Any]:
    position = ctx.db.scalar("SELECT coalesce(max(position), 0) + 1 FROM ems.tasks WHERE project_id = :p AND status = 'todo'", p=project_id)
    task_id = uuid.uuid4()
    ctx.db.execute("INSERT INTO ems.tasks (id, org_id, project_id, title, assignee_id, due_at, estimate_minutes, billable, position) "
                   "VALUES (:id, :org, :p, :t, :a, :d, :est, :b, :pos)",
                   id=task_id, org=ctx.org_id, p=project_id, t=title, a=assignee_id, d=due_at, est=estimate_minutes, b=billable,
                   pos=position)
    return {"id": task_id, "status": "todo", "position": position, "version": 1}


def apply_template(ctx: Ctx, project_id: uuid.UUID, template: str, billable: bool) -> int:
    for title in TEMPLATES[template]:
        insert_task(ctx, project_id, title, billable=billable)
    return len(TEMPLATES[template])
