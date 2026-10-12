"""Invoice and payment records (API-053/054). EMS records money; it does not send invoices or collect payment in R1."""
import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Query
from pydantic import Field
from sqlalchemy.exc import IntegrityError

from app.platform.context import SessionCtx
from app.platform.db import Db
from app.platform.errors import ApiError, invalid, not_found
from app.platform.idempotency import IdemKey, run_once
from app.platform.pagination import clamp_limit, decode_cursor, page
from app.platform.responses import ok
from app.platform.schema import Body, Currency, Money
from app.platform.serialize import money

router = APIRouter(prefix="/api/v1/invoices")


def outstanding(db: Db, invoice_id: uuid.UUID, amount: Decimal) -> Decimal:
    paid = db.scalar("SELECT coalesce(sum(amount), 0) FROM ems.payments WHERE invoice_id = :i", i=invoice_id)
    return Decimal(amount) - Decimal(paid)


# ------------------------------------------------------------------------------------------------ invoice list (web)
@router.get("")
def list_invoices(ctx: SessionCtx, status: Literal["sent", "partially_paid", "paid", "void"] | None = None, client_id: uuid.UUID | None = None,
                  cursor: str | None = None, limit: Annotated[int | None, Query()] = None):
    """Recorded invoices with what is still outstanding. Read-only companion to API-053/054."""
    ctx.require("finance.manage", "Only the CEO and CFO can see invoices.")
    limit, after = clamp_limit(limit), decode_cursor(cursor, 2)
    rows = ctx.db.all(
        "SELECT i.id, i.number, i.client_id, co.name AS client, i.project_id, p.name AS project, i.amount, i.currency, i.issued_on, "
        "i.due_on, i.status, coalesce(pay.paid, 0) AS paid FROM ems.invoices i JOIN ems.clients c ON c.id = i.client_id "
        "JOIN ems.companies co ON co.id = c.company_id LEFT JOIN ems.projects p ON p.id = i.project_id "
        "LEFT JOIN (SELECT invoice_id, sum(amount) AS paid FROM ems.payments GROUP BY invoice_id) pay ON pay.invoice_id = i.id "
        "WHERE (CAST(:st AS text) IS NULL OR i.status = :st) AND (CAST(:c AS uuid) IS NULL OR i.client_id = :c) "
        "AND (CAST(:a_d AS date) IS NULL OR (i.issued_on, i.id) < (CAST(:a_d AS date), CAST(:a_id AS uuid))) "
        "ORDER BY i.issued_on DESC, i.id DESC LIMIT :lim",
        st=status, c=client_id, a_d=after[0] if after else None, a_id=after[1] if after else None, lim=limit + 1)
    rows, next_cursor = page(rows, limit, lambda r: [r["issued_on"].isoformat(), str(r["id"])])
    keys = ("id", "number", "client_id", "client", "project_id", "project", "currency", "issued_on", "due_on", "status")
    return ok({"items": [{**{k: r[k] for k in keys}, "amount": money(r["amount"]), "paid": money(r["paid"]),
                          "outstanding": money(Decimal(r["amount"]) - Decimal(r["paid"]))} for r in rows],
               "next_cursor": next_cursor})


# ------------------------------------------------------------------------------------------------ API-053
class InvoiceIn(Body):
    client_id: uuid.UUID
    project_id: uuid.UUID | None = None
    number: str = Field(min_length=1, max_length=60)
    amount: Money
    currency: Currency
    issued_on: dt.date
    due_on: dt.date
    time_entry_ids: list[uuid.UUID] = Field(default_factory=list, max_length=1000)


@router.post("", status_code=201)
def record_invoice(body: InvoiceIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("finance.manage", "Only the CEO and CFO can record invoices.")
    if body.amount <= 0:
        raise invalid("The invoice amount must be more than zero.", {"amount": "> 0"})
    if body.due_on < body.issued_on:
        raise invalid("The due date cannot be before the issue date.", {"due_on": "On or after issued_on."})

    def handler():
        db = ctx.db
        if not db.scalar("SELECT 1 FROM ems.clients WHERE id = :c", c=body.client_id):
            raise invalid("That client does not exist.", {"client_id": "Unknown client."})
        if body.project_id and not db.scalar("SELECT 1 FROM ems.projects WHERE id = :p AND client_id = :c", p=body.project_id, c=body.client_id):
            raise invalid("That project does not belong to this client.", {"project_id": "Not a project of this client."})
        if db.scalar("SELECT 1 FROM ems.invoices WHERE number = :n", n=body.number):
            raise ApiError("INVOICE_NUMBER_TAKEN", f"Invoice number {body.number} already exists.")
        entry_ids = list(dict.fromkeys(body.time_entry_ids))
        if entry_ids:
            # Entries must be billable, not yet invoiced, and belong to this client's projects (to this project if given).
            eligible = db.scalar(
                "SELECT count(*) FROM ems.time_entries e JOIN ems.tasks t ON t.id = e.task_id JOIN ems.projects p ON p.id = t.project_id "
                "WHERE e.id = ANY(:ids) AND e.billable AND e.invoice_id IS NULL AND p.client_id = :c "
                "AND (CAST(:p AS uuid) IS NULL OR p.id = :p)", ids=entry_ids, c=body.client_id, p=body.project_id)
            if eligible != len(entry_ids):
                raise invalid("Some time entries cannot go on this invoice (not billable, already invoiced, or another client's).",
                              {"time_entry_ids": "Check the selected entries."})
        invoice_id = uuid.uuid4()
        try:
            with db.savepoint():
                db.execute("INSERT INTO ems.invoices (id, org_id, client_id, project_id, number, amount, currency, issued_on, due_on) "
                           "VALUES (:id, :org, :c, :p, :n, :a, :cur, :iss, :due)",
                           id=invoice_id, org=ctx.org_id, c=body.client_id, p=body.project_id, n=body.number, a=body.amount,
                           cur=body.currency, iss=body.issued_on, due=body.due_on)
        except IntegrityError as exc:                    # concurrent duplicate number
            raise ApiError("INVOICE_NUMBER_TAKEN", f"Invoice number {body.number} already exists.") from exc
        if entry_ids:
            # The check above can race a concurrent invoice for the same entries; this conditional update cannot. A second
            # request waits for the first to commit, then finds the entries already invoiced and rolls back.
            billed = db.execute("UPDATE ems.time_entries SET invoice_id = :inv WHERE id = ANY(:ids) AND billable AND invoice_id IS NULL",
                                inv=invoice_id, ids=entry_ids).rowcount
            if billed != len(entry_ids):
                raise invalid("Some time entries were invoiced by another request. Reload and choose the entries again.",
                              {"time_entry_ids": "Already invoiced."})
        ctx.audit("invoice.recorded", "invoice", invoice_id)
        ctx.emit("invoice.recorded", {"invoice_id": str(invoice_id), "client_id": str(body.client_id)})
        return ok({"id": invoice_id, "status": "sent", "outstanding": money(body.amount)}, f"Invoice {body.number} recorded.", status=201)

    return run_once(ctx, idem, handler)


# ------------------------------------------------------------------------------------------------ API-054
class PaymentIn(Body):
    amount: Money
    received_on: dt.date
    method: Literal["bank_transfer", "card", "cash", "cheque", "other"]


@router.post("/{invoice_id}/payments", status_code=201)
def record_payment(invoice_id: uuid.UUID, body: PaymentIn, ctx: SessionCtx, idem: IdemKey):
    ctx.require("finance.manage", "Only the CEO and CFO can record payments.")
    if body.amount <= 0:
        raise invalid("The payment amount must be more than zero.", {"amount": "> 0"})

    def handler():
        db = ctx.db
        inv = db.one("SELECT id, amount, currency, status FROM ems.invoices WHERE id = :i FOR UPDATE", i=invoice_id)  # serializes payments
        if inv is None:
            raise not_found("Invoice")
        if inv["status"] in ("void", "draft"):
            raise ApiError("INVALID_TRANSITION", f"Payments cannot be recorded on a {inv['status']} invoice.",
                           {"from": inv["status"], "allowed": ["sent", "partially_paid"]})
        remaining = outstanding(db, invoice_id, inv["amount"])
        if body.amount > remaining:
            raise ApiError("OVERPAYMENT", f"Payment exceeds the outstanding amount of {money(remaining)} {inv['currency']}.",
                           {"outstanding": money(remaining)})
        payment_id = uuid.uuid4()
        db.execute("INSERT INTO ems.payments (id, org_id, invoice_id, amount, received_on, method) VALUES (:id, :org, :i, :a, :r, :m)",
                   id=payment_id, org=ctx.org_id, i=invoice_id, a=body.amount, r=body.received_on, m=body.method)
        left = remaining - body.amount
        status = "paid" if left == 0 else "partially_paid"
        db.execute("UPDATE ems.invoices SET status = :s, version = version + 1 WHERE id = :i", s=status, i=invoice_id)
        ctx.audit("payment.recorded", "payment", payment_id)
        ctx.emit("payment.recorded", {"payment_id": str(payment_id), "invoice_id": str(invoice_id)})
        return ok({"payment_id": payment_id, "invoice_status": status, "outstanding": money(left)}, status=201)

    return run_once(ctx, idem, handler)
