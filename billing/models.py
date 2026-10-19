"""Invoices and payments.

The outstanding balance is always an aggregate (SUM of payments against the
invoice amount_due); it is never a stored, editable column.
"""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import SoftDeleteModel, TimeStampedModel


class Invoice(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        ISSUED = "ISSUED", "Issued"
        VOID = "VOID", "Void"

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="invoices"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="invoices_created",
    )

    class Meta:
        ordering = ["-due_date", "student__admission_no"]
        constraints = [
            models.CheckConstraint(condition=Q(amount_due__gt=0), name="invoice_amount_due_gt_0"),
            models.CheckConstraint(
                condition=Q(period_end__gte=F("period_start")), name="invoice_period_ordered"
            ),
            models.UniqueConstraint(
                fields=["student", "period_start", "period_end"], name="uniq_invoice_student_period"
            ),
        ]
        indexes = [
            models.Index(fields=["status", "due_date"], name="invoice_status_due_idx"),
            models.Index(fields=["student"], name="invoice_student_idx"),
        ]

    def __str__(self) -> str:
        return f"Invoice {self.student} ({self.period_start:%Y-%m} - {self.period_end:%Y-%m})"


class Payment(SoftDeleteModel):
    class Method(models.TextChoices):
        CASH = "CASH", "Cash"
        BANK_TRANSFER = "BANK_TRANSFER", "Bank transfer"
        CARD = "CARD", "Card"
        UPI = "UPI", "UPI"

    invoice = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    paid_on = models.DateField()
    method = models.CharField(max_length=16, choices=Method.choices)
    receipt_no = models.CharField(max_length=40, unique=True)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="payments_recorded",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-paid_on", "-created_at"]
        constraints = [
            models.CheckConstraint(condition=Q(amount__gt=0), name="payment_amount_gt_0")
        ]
        indexes = [models.Index(fields=["paid_on"], name="payment_paid_on_idx")]

    def __str__(self) -> str:
        return f"{self.receipt_no}: {self.amount} on {self.paid_on}"
