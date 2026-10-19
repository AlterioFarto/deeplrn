"""Billing domain tests: invoice state machine and payment rules."""

from decimal import Decimal

import pytest

from billing import services
from common.exceptions import ConflictError

pytestmark = pytest.mark.django_db


def test_invoice_requires_ordered_period(student, admin):
    with pytest.raises(ConflictError):
        services.create_invoice(
            student=student,
            period_start="2025-01-10",
            period_end="2025-01-09",
            amount_due=Decimal("100.00"),
            due_date="2025-01-12",
            actor=admin,
        )


def test_void_with_payments_blocked(student, invoice, admin):
    services.record_payment(
        invoice=invoice,
        amount=Decimal("100.00"),
        paid_on="2025-01-15",
        method="cash",
        receipt_no="R1",
        recorded_by=admin,
        actor=admin,
    )
    with pytest.raises(ConflictError):
        services.void_invoice(invoice=invoice, actor=admin)


def test_outstanding_pays_down(student, invoice, admin):
    services.record_payment(
        invoice=invoice,
        amount=Decimal("200.00"),
        paid_on="2025-01-15",
        method="cash",
        receipt_no="R2",
        recorded_by=admin,
        actor=admin,
    )
    today = services.outstanding_for_invoice(invoice)
    assert today == Decimal("300.00")


def test_payment_cannot_exceed_outstanding(student, invoice, admin):
    services.record_payment(
        invoice=invoice,
        amount=Decimal("400.00"),
        paid_on="2025-01-15",
        method="cash",
        receipt_no="R3",
        recorded_by=admin,
        actor=admin,
    )
    with pytest.raises(ConflictError):
        services.record_payment(
            invoice=invoice,
            amount=Decimal("200.00"),
            paid_on="2025-01-16",
            method="cash",
            receipt_no="R4",
            recorded_by=admin,
            actor=admin,
        )


def test_soft_deleted_payment_counts_not_outstanding(student, invoice, admin):
    payment = services.record_payment(
        invoice=invoice,
        amount=Decimal("500.00"),
        paid_on="2025-01-15",
        method="cash",
        receipt_no="R5",
        recorded_by=admin,
        actor=admin,
    )
    assert services.outstanding_for_invoice(invoice) == 0
    services.delete_payment(payment=payment, actor=admin)
    assert services.outstanding_for_invoice(invoice) == Decimal("500.00")


def test_only_admin_deletes_payment(student, invoice, mentor):
    payment = services.record_payment(
        invoice=invoice,
        amount=Decimal("100.00"),
        paid_on="2025-01-15",
        method="cash",
        receipt_no="R6",
        recorded_by=mentor,
        actor=mentor,
    )
    with pytest.raises(ConflictError):
        services.delete_payment(payment=payment, actor=mentor)


def test_edit_draft_only(student, invoice, admin):
    with pytest.raises(ConflictError):
        services.update_invoice(
            invoice=invoice,
            period_start="2025-01-01",
            period_end="2025-01-31",
            amount_due=Decimal("600.00"),
            due_date="2025-01-31",
            actor=admin,
        )
