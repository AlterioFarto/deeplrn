"""Billing read paths: balances as aggregates, scoped to the boundary."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db.models import (
    BooleanField,
    Case,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce
from django.utils import timezone

from billing.models import Invoice, Payment
from common.scoping import scoped_queryset

if TYPE_CHECKING:
    from accounts.models import User as UserType
    from students.models import Student as StudentType

DEC = DecimalField(max_digits=10, decimal_places=2)
_ZERO = Value(Decimal("0.00"), output_field=DEC)


def invoice_list_qs(
    *, user: "UserType", q: str | None = None, status: str | None = None
) -> QuerySet[Invoice]:
    """Invoices with paid/outstanding/overdue computed in SQL."""
    today = timezone.localdate()
    qs = (
        Invoice.objects.select_related("student__group")
        .annotate(
            paid_total=Coalesce(
                Sum("payments__amount", filter=Q(payments__deleted_at__isnull=True)),
                _ZERO,
                output_field=DEC,
            ),
        )
        .annotate(
            outstanding=Case(
                When(status=Invoice.Status.VOID, then=Value(Decimal("0.00"))),
                default=ExpressionWrapper(F("amount_due") - F("paid_total"), output_field=DEC),
                output_field=DEC,
            ),
        )
        .annotate(
            overdue=Case(
                When(due_date__lt=today, status=Invoice.Status.ISSUED, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            ),
        )
    )
    qs = scoped_queryset(qs, user)
    if q:
        qs = qs.filter(
            Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(student__admission_no__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-due_date", "student__admission_no")


def invoice_detail_qs(*, user: "UserType") -> QuerySet[Invoice]:
    return scoped_queryset(
        Invoice.objects.select_related("student__group").prefetch_related("payments__recorded_by"),
        user,
    )


def invoice_list_for_student(student: "StudentType", *, user: "UserType") -> QuerySet[Invoice]:
    return invoice_list_qs(user=user).filter(student=student)


def invoice_outstanding(student: "StudentType") -> Decimal:
    """Total outstanding across issued invoices for a student."""
    rows = (
        Invoice.objects.filter(student=student, status=Invoice.Status.ISSUED)
        .annotate(
            paid=Coalesce(
                Sum("payments__amount", filter=Q(payments__deleted_at__isnull=True)),
                _ZERO,
                output_field=DEC,
            ),
        )
        .aggregate(
            due=Sum("amount_due"),
            collected=Coalesce(Sum("paid"), _ZERO, output_field=DEC),
        )
    )
    return Decimal(rows["due"] or 0) - Decimal(rows["collected"] or 0)


def outstanding_total(*, user: "UserType") -> Decimal:
    total = (
        invoice_list_qs(user=user)
        .filter(status=Invoice.Status.ISSUED)
        .aggregate(total=Sum("outstanding"))["total"]
    )
    return Decimal(total or 0)


def paid_total(*, start: date | None = None, end: date | None = None) -> Decimal:
    qs = Payment.objects.filter(deleted_at__isnull=True)
    if start:
        qs = qs.filter(paid_on__gte=start)
    if end:
        qs = qs.filter(paid_on__lte=end)
    return Decimal(qs.aggregate(total=Sum("amount"))["total"] or 0)
