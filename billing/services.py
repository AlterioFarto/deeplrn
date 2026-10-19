"""Billing mutations: invoices and the payment state machine."""

from datetime import date
from decimal import Decimal

from django.db import transaction
from django.db.models import Sum

from accounts.models import User
from billing.models import Invoice, Payment
from common.audit import log_action, make_diff, snapshot
from common.exceptions import ConflictError
from common.scoping import assert_can_access
from students.models import Student


def outstanding_for_invoice(invoice: Invoice) -> Decimal:
    """Single source for outstanding balance (aggregate, never stored)."""
    paid = invoice.payments.filter(deleted_at__isnull=True).aggregate(total=Sum("amount"))["total"]
    return Decimal(invoice.amount_due) - Decimal(paid or 0)


def _assert_can_manage_invoice(actor: User, invoice: Invoice) -> None:
    if invoice.student_id:
        assert_can_access(actor, invoice.student)


@transaction.atomic
def create_invoice(
    *,
    student: Student,
    period_start: date,
    period_end: date,
    amount_due: Decimal,
    due_date: date,
    status: str = Invoice.Status.DRAFT,
    actor: User | None = None,
) -> Invoice:
    assert_can_access(actor, student)
    if period_end < period_start:
        raise ConflictError("Billing period end must be on or after its start.")
    if amount_due <= 0:
        raise ConflictError("Amount due must be greater than zero.")
    invoice = Invoice.objects.create(
        student=student,
        period_start=period_start,
        period_end=period_end,
        amount_due=amount_due,
        due_date=due_date,
        status=status,
        created_by=actor,
    )
    log_action(actor=actor, action="create", obj=invoice)
    return invoice


@transaction.atomic
def update_invoice(
    *,
    invoice: Invoice,
    period_start: date,
    period_end: date,
    amount_due: Decimal,
    due_date: date,
    actor: User | None = None,
) -> Invoice:
    """Invoices can be edited while in DRAFT; issuing/voiding are separate moves."""
    assert_can_access(actor, invoice.student)
    if invoice.status != Invoice.Status.DRAFT:
        raise ConflictError("Only draft invoices can be edited.")
    if period_end < period_start:
        raise ConflictError("Billing period end must be on or after its start.")
    if amount_due <= 0:
        raise ConflictError("Amount due must be greater than zero.")
    old_amount = invoice.amount_due
    if (
        amount_due < old_amount
        and (
            payments := invoice.payments.filter(deleted_at__isnull=True).aggregate(
                total=Sum("amount")
            )["total"]
        )
        and amount_due < payments
    ):
        raise ConflictError("Amount due cannot fall below the payments already received.")
    before = snapshot(invoice, ("period_start", "period_end", "amount_due", "due_date"))
    fields = ("period_start", "period_end", "amount_due", "due_date")
    invoice.period_start = period_start
    invoice.period_end = period_end
    invoice.amount_due = amount_due
    invoice.due_date = due_date
    invoice.save()
    log_action(actor=actor, action="update", obj=invoice, diff=make_diff(before, invoice, fields))
    return invoice


@transaction.atomic
def issue_invoice(*, invoice: Invoice, actor: User | None = None) -> Invoice:
    assert_can_access(actor, invoice.student)
    if invoice.status != Invoice.Status.DRAFT:
        raise ConflictError("Only draft invoices can be issued.")
    before = snapshot(invoice, ("status",))
    invoice.status = Invoice.Status.ISSUED
    invoice.save(update_fields=["status", "updated_at"])
    log_action(
        actor=actor, action="update", obj=invoice, diff=make_diff(before, invoice, ("status",))
    )
    return invoice


@transaction.atomic
def void_invoice(*, invoice: Invoice, actor: User | None = None) -> Invoice:
    assert_can_access(actor, invoice.student)
    if invoice.status == Invoice.Status.VOID:
        return invoice
    if outstanding_for_invoice(invoice) < invoice.amount_due:
        raise ConflictError("This invoice already has payments; void it after refunding them.")
    before = snapshot(invoice, ("status",))
    invoice.status = Invoice.Status.VOID
    invoice.save(update_fields=["status", "updated_at"])
    log_action(
        actor=actor, action="update", obj=invoice, diff=make_diff(before, invoice, ("status",))
    )
    return invoice


@transaction.atomic
def record_payment(
    *,
    invoice: Invoice,
    amount: Decimal,
    paid_on: date,
    method: str,
    receipt_no: str,
    notes: str = "",
    recorded_by: User | None = None,
    actor: User | None = None,
) -> Payment:
    assert_can_access(actor, invoice.student)
    if invoice.status == Invoice.Status.DRAFT:
        raise ConflictError("Issue the invoice before recording payments.")
    if invoice.status == Invoice.Status.VOID:
        raise ConflictError("Void invoices cannot receive payments.")
    if amount <= 0:
        raise ConflictError("Payment amount must be greater than zero.")
    locked_invoice = Invoice.objects.select_for_update().get(pk=invoice.pk)
    remaining = outstanding_for_invoice(locked_invoice)
    if amount > remaining:
        raise ConflictError(f"Payment exceeds the remaining balance ({remaining}).")
    payment = Payment.objects.create(
        invoice=locked_invoice,
        amount=amount,
        paid_on=paid_on,
        method=method,
        receipt_no=receipt_no.strip(),
        recorded_by=recorded_by,
        notes=notes,
    )
    log_action(actor=actor, action="create", obj=payment)
    return payment


@transaction.atomic
def delete_payment(*, payment: Payment, actor: User | None = None) -> Payment:
    """Soft-delete a payment; the outstanding balance recomputes automatically."""
    assert_can_access(actor, payment.invoice.student)
    if actor is None or actor.role != "ADMIN":
        raise ConflictError("Only admins can reverse payments.")
    payment.delete()
    log_action(actor=actor, action="soft_delete", obj=payment)
    return payment


@transaction.atomic
def restore_payment(*, payment: Payment, actor: User | None = None) -> Payment:
    if actor is None or actor.role != "ADMIN":
        raise ConflictError("Only admins can restore payments.")
    payment.restore()
    log_action(actor=actor, action="restore", obj=payment)
    return payment
