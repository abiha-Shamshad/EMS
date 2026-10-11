"""Projects, Kanban tasks and time (API-038..044)."""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field

from app.platform.context import SessionCtx
from app.platform.errors import ApiError, invalid, not_found, version_conflict
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body, Currency, ExpectedVersion, Money
from app.platform.serialize import money
from app.platform.timeutil import utcnow
from app.projects import service as projects

router = APIRouter(prefix="/api/v1")
COLUMN_CAP = 200
FUTURE_SKEW = dt.timedelta(minutes=5)


# ------------------------------------------------------------------------------------------------ API-038
@router.get("/projects")
def list_projects(ctx: SessionCtx, status: Literal["planned", "active", "on_hold", "completed", "cancelled"] | None = None,
                  client_id: uuid.UUID | None = None, cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    visible = "" if ctx.can("projects.manage") else (
        " AND (p.owner_id = :me OR EXISTS (SELECT 1 FROM ems.tasks x WHERE x.project_id = p.id AND x.assignee_id = :me))")
    rows = ctx.db.all(
        "SELECT p.id, p.name, co.name AS client, p.status, p.billing_type, p.budget_amount, p.currency, p.owner_id, p.version, "  # noqa: S608 - only fixed SQL fragments are interpolated
        "count(t.id) FILTER (WHERE t.status = 'todo') AS todo, count(t.id) FILTER (WHERE t.status = 'active') AS active, "
        "count(t.id) FILTER (WHERE t.status = 'review') AS review, count(t.id) FILTER (WHERE t.status = 'done') AS done, "
        "count(t.id) FILTER (WHERE t.status <> 'done' AND t.due_at < now()) AS overdue "
        "FROM ems.projects p LEFT JOIN ems.clients c ON c.id = p.client_id LEFT JOIN ems.companies co ON co.id = c.company_id "
        "LEFT JOIN ems.tasks t ON t.project_id = p.id "
        f"WHERE (CAST(:status AS text) IS NULL OR p.status = :status) AND (CAST(:client AS uuid) IS NULL OR p.client_id = :client){visible} "
        "AND (CAST(:a_name AS text) IS NULL OR (p.name, p.id) > (:a_name, CAST(:a_id AS uuid))) "
        "GROUP BY p.id, co.name ORDER BY p.name, p.id LIMIT :lim",
        status=status, client=client_id, me=ctx.user_id, a_name=after[0] if after else None, a_id=after[1] if after else None,
        lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["name"], str(r["id"])])
    costs = projects.cost_to_date(ctx.db, [r["id"] for r in rows])
    finance = ctx.can("finance.manage")
    items = []
    for r in rows:
        total = r["todo"] + r["active"] + r["review"] + r["done"]
        item = {"id": r["id"], "name": r["name"], "client": r["client"], "status": r["status"], "billing_type": r["billing_type"],
                "progress_pct": round(100 * r["done"] / total) if total else 0,
                "tasks": {k: r[k] for k in ("todo", "active", "review", "done")}, "overdue": r["overdue"], "version": r["version"],
                "budget": None}
        # Budget figures appear only for finance.manage and the project owner (API-038 rule).
        if r["budget_amount"] is not None and (finance or r["owner_id"] == ctx.user_id):
            c = costs.get(r["id"], {"cost": Decimal(0), "rates_missing": 0})
            item["budget"] = {"amount": money(r["budget_amount"]), "cost_to_date": money(c["cost"]), "currency": r["currency"],
                              "ratio": str((c["cost"] / r["budget_amount"]).quantize(Decimal("0.01"))) if r["budget_amount"] else None,
                              "entries_without_cost_rate": c["rates_missing"]}
        items.append(item)
    return ok({"items": items, "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-039
class ProjectIn(Body):
    name: str = Field(min_length=1, max_length=200)
    client_id: uuid.UUID | None = None
    billing_type: Literal["fixed", "hourly", "retainer", "internal"]
    budget_amount: Money | None = None
    hourly_rate: Money | None = None
    currency: Currency | None = None
    owner_id: uuid.UUID | None = None


@router.post("/projects", status_code=201)
def create_project(body: ProjectIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("projects.manage", "Only leadership and managers can create projects.")
    if body.billing_type == "hourly" and (body.hourly_rate is None or body.currency is None):
        raise invalid("Hourly projects need an hourly rate and currency.",
                      {k: "Required for hourly billing." for k in ("hourly_rate", "currency") if getattr(body, k) is None})
    if body.billing_type != "internal" and body.client_id is None:
        raise invalid("Client projects need a client.", {"client_id": "Required unless billing is internal."})

    def handler():
        db = ctx.db
        if body.client_id and not db.scalar("SELECT 1 FROM ems.clients WHERE id = :c", c=body.client_id):
            raise invalid("That client does not exist.", {"client_id": "Unknown client."})
        owner = body.owner_id or ctx.user_id
        projects.require_active_member(db, owner, "owner")
        currency = body.currency or (ctx.org["base_currency"] if body.budget_amount is not None else None)
        project_id = projects.insert_project(ctx, name=body.name, client_id=body.client_id, billing_type=body.billing_type,
                                             budget_amount=body.budget_amount, hourly_rate=body.hourly_rate, currency=currency,
                                             owner_id=owner)
        ctx.audit("project.created", "project", project_id)
        ctx.emit("project.created", {"project_id": str(project_id)})
        return ok({"id": project_id, "name": body.name, "status": "planned", "billing_type": body.billing_type, "version": 1},
                  "Project created.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-040
@router.get("/projects/{project_id}/board")
def project_board(project_id: uuid.UUID, ctx: SessionCtx, assignee_id: uuid.UUID | None = None):
    project = projects.project_for(ctx, project_id)
    client = ctx.db.scalar("SELECT co.name FROM ems.clients c JOIN ems.companies co ON co.id = c.company_id WHERE c.id = :c",
                           c=project["client_id"]) if project["client_id"] else None
    columns, truncated = {}, {}
    for status in ("todo", "active", "review", "done"):
        order = "t.position, t.created_at" if status != "done" else "t.created_at DESC"
        rows = ctx.db.all(
            "SELECT t.id, t.title, t.assignee_id, u.name AS assignee, t.due_at, t.position, t.version, t.billable, t.estimate_minutes, "  # noqa: S608 - only fixed SQL fragments are interpolated
            "(SELECT coalesce(sum(minutes), 0) FROM ems.time_entries e WHERE e.task_id = t.id) AS minutes_logged "
            "FROM ems.tasks t LEFT JOIN ems.users u ON u.id = t.assignee_id "
            f"WHERE t.project_id = :p AND t.status = :s AND (CAST(:a AS uuid) IS NULL OR t.assignee_id = :a) ORDER BY {order} LIMIT :lim",
            p=project_id, s=status, a=assignee_id, lim=COLUMN_CAP + 1)
        truncated[status] = len(rows) > COLUMN_CAP
        columns[status] = rows[:COLUMN_CAP]
    return ok({"project": {"id": project["id"], "name": project["name"], "client": client, "status": project["status"],
                           "billing_type": project["billing_type"], "version": project["version"]},
               "columns": columns, "column_truncated": truncated})


# ------------------------------------------------------------------------------------------------ API-041
class TaskIn(Body):
    title: str = Field(min_length=1, max_length=200)
    assignee_id: uuid.UUID | None = None
    due_at: dt.datetime | None = None
    estimate_minutes: int | None = Field(default=None, gt=0)
    billable: bool = True


@router.post("/projects/{project_id}/tasks", status_code=201)
def create_task(project_id: uuid.UUID, body: TaskIn, ctx: SessionCtx, idem: IdemKey):
    def handler():
        projects.project_for(ctx, project_id)
        projects.require_active_member(ctx.db, body.assignee_id)
        task = projects.insert_task(ctx, project_id, body.title, assignee_id=body.assignee_id, due_at=body.due_at,
                                    estimate_minutes=body.estimate_minutes, billable=body.billable)
        ctx.audit("task.created", "task", task["id"])
        ctx.emit("task.created", {"task_id": str(task["id"]), "project_id": str(project_id),
                                  "assignee_id": str(body.assignee_id) if body.assignee_id else None})
        return ok(task, "Task created.", status=201)

    return run_once(ctx, idem, handler)


def _task_for(ctx, task_id: uuid.UUID) -> dict:
    task = ctx.db.one("SELECT id, project_id, title, status, assignee_id, due_at, billable, position, version "
                      "FROM ems.tasks WHERE id = :t FOR UPDATE", t=task_id)
    if task is None:
        raise not_found("Task")
    projects.project_for(ctx, task["project_id"])        # NOT_FOUND unless the caller can see the project
    return task


# ------------------------------------------------------------------------------------------------ API-042
class TaskUpdateIn(Body):
    expected_version: ExpectedVersion
    title: str | None = Field(default=None, min_length=1, max_length=200)
    assignee_id: uuid.UUID | None = None
    due_at: dt.datetime | None = None
    estimate_minutes: int | None = Field(default=None, gt=0)
    billable: bool | None = None


@router.patch("/tasks/{task_id}")
def update_task(task_id: uuid.UUID, body: TaskUpdateIn, ctx: SessionCtx):
    fields = body.model_fields_set - {"expected_version"}
    if not fields:
        raise invalid("Nothing to change.")
    for required in ("title", "billable"):
        if required in fields and getattr(body, required) is None:
            raise invalid(f"{required} cannot be empty.", {required: "Required."})
    task = _task_for(ctx, task_id)
    if task["version"] != body.expected_version:
        raise version_conflict(task["version"], "This task was changed by someone else.")
    if "assignee_id" in fields:
        projects.require_active_member(ctx.db, body.assignee_id)
    values = body.model_dump(include=fields)
    sets = ", ".join(f"{f} = :{f}" for f in sorted(fields))
    row = ctx.db.one(f"UPDATE ems.tasks SET {sets}, version = version + 1 WHERE id = :tid "  # noqa: S608 - fixed names
                     "RETURNING id, title, assignee_id, due_at, estimate_minutes, billable, version", tid=task_id, **values)
    ctx.audit("task.updated", "task", task_id, fields)
    ctx.emit("task.updated", {"task_id": str(task_id), "project_id": str(task["project_id"]), "fields": sorted(fields),
                              "assignee_id": str(row["assignee_id"]) if row["assignee_id"] else None})
    return ok({"id": row["id"], **{f: row[f] for f in fields}, "version": row["version"]})


# ------------------------------------------------------------------------------------------------ API-043
class MoveIn(Body):
    expected_version: ExpectedVersion
    to_status: Literal["todo", "active", "review", "done"]
    position: int = Field(ge=0)


@router.post("/tasks/{task_id}/move")
def move_task(task_id: uuid.UUID, body: MoveIn, ctx: SessionCtx):
    task = _task_for(ctx, task_id)
    if task["version"] != body.expected_version:
        raise version_conflict(task["version"], "This task was changed by someone else.")
    if body.to_status != task["status"] and body.to_status not in projects.TRANSITIONS[task["status"]]:
        hint = "Tasks move to Done only from Review." if body.to_status == "done" else "That move is not allowed on the board."
        raise ApiError("INVALID_TRANSITION", hint, {"from": task["status"], "to": body.to_status,
                                                    "allowed": sorted(projects.TRANSITIONS[task["status"]])})
    row = ctx.db.one("UPDATE ems.tasks SET status = :s, position = :p, version = version + 1 WHERE id = :t "
                     "RETURNING id, status, position, version", s=body.to_status, p=body.position, t=task_id)
    if body.to_status == "active" and task["status"] != "active":
        # Work has started: a planned project becomes active, and an onboarding client becomes active (Section 13).
        client_id = ctx.db.scalar("UPDATE ems.projects SET status = CASE WHEN status = 'planned' THEN 'active' ELSE status END, "
                                  "version = version + CASE WHEN status = 'planned' THEN 1 ELSE 0 END "
                                  "WHERE id = :p RETURNING client_id", p=task["project_id"])
        if client_id:
            ctx.db.execute("UPDATE ems.clients SET status = 'active' WHERE id = :c AND status = 'onboarding'", c=client_id)
    ctx.audit("task.moved", "task", task_id, ["status", "position"])
    if body.to_status != task["status"]:
        ctx.emit("task.status_changed", {"task_id": str(task_id), "project_id": str(task["project_id"]),
                                         "from_status": task["status"], "to_status": body.to_status})
    return ok(row)


# ------------------------------------------------------------------------------------------------ API-044
class TimeIn(Body):
    started_at: dt.datetime
    minutes: int = Field(ge=1, le=1440)
    billable: bool | None = None
    note: str | None = Field(default=None, max_length=2000)


@router.post("/tasks/{task_id}/time-entries", status_code=201)
def log_time(task_id: uuid.UUID, body: TimeIn, ctx: SessionCtx, idem: IdemKey):
    if body.started_at.tzinfo is None:
        raise invalid("Send started_at in UTC with a Z suffix.", {"started_at": "Timezone required."})
    if body.started_at + dt.timedelta(minutes=body.minutes) > utcnow() + FUTURE_SKEW:
        raise invalid("Time cannot be logged in the future.", {"started_at": "In the future."})

    def handler():
        db = ctx.db
        task = _task_for(ctx, task_id)
        project = db.one("SELECT owner_id FROM ems.projects WHERE id = :p", p=task["project_id"])
        if not (task["assignee_id"] == ctx.user_id or project["owner_id"] == ctx.user_id or ctx.can("projects.manage")):
            raise ApiError("AUTHORIZATION_DENIED", "Only the assignee or a project manager can log time on this task.")
        end = body.started_at + dt.timedelta(minutes=body.minutes)
        overlap = db.scalar("SELECT id FROM ems.work_sessions WHERE user_id = :u AND started_at < :e "
                            "AND coalesce(ended_at, now()) > :s ORDER BY started_at LIMIT 1", u=ctx.user_id, s=body.started_at, e=end)
        if overlap:
            raise ApiError("TIME_OVERLAPS_SESSION", "This time overlaps your Room session, which already counted it.",
                           {"session_id": overlap})
        billable = task["billable"] if body.billable is None else body.billable
        entry_id = uuid.uuid4()
        db.execute("INSERT INTO ems.time_entries (id, org_id, task_id, user_id, started_at, minutes, source, billable) "
                   "VALUES (:id, :org, :t, :u, :s, :m, 'manual', :b)",
                   id=entry_id, org=ctx.org_id, t=task_id, u=ctx.user_id, s=body.started_at, m=body.minutes, b=billable)
        if body.note:                                    # time_entries has no note column; the note is kept on the task
            db.execute("INSERT INTO ems.activities (id, org_id, entity_type, entity_id, kind, note, actor_id, occurred_at) "
                       "VALUES (:id, :org, 'task', :t, 'note', :n, :u, :at)",
                       id=uuid.uuid4(), org=ctx.org_id, t=task_id, n=body.note, u=ctx.user_id, at=body.started_at)
        ctx.audit("time.logged", "time_entry", entry_id)
        ctx.emit("time.logged", {"time_entry_id": str(entry_id), "task_id": str(task_id), "minutes": body.minutes})
        return ok({"time_entry_id": entry_id, "source": "manual", "minutes": body.minutes, "billable": billable}, status=201)

    return run_once(ctx, idem, handler)
