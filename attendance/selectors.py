"""Attendance read paths: scoped lists and policy-aware percentages."""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from django.db.models import (
    Case,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Q,
    QuerySet,
    Value,
    When,
)

from attendance.models import Attendance, Policy
from students.models import Student

if TYPE_CHECKING:
    from accounts.models import User as UserType


def numerator_q(policy: Policy, prefix: str = "attendance") -> Q:
    path = f"{prefix}__status" if prefix else "status"
    counted = Q(**{path: Attendance.Status.PRESENT})
    if policy.count_late_as_present:
        counted |= Q(**{path: Attendance.Status.LATE})
    if policy.count_excused_as_present:
        counted |= Q(**{path: Attendance.Status.EXCUSED})
    return counted


def annotate_attendance(
    student_qs: QuerySet[Student], *, start: date | None = None, end: date | None = None
) -> QuerySet[Student]:
    """Annotate attendance totals and percentage; policy-driven numerator."""
    policy = Policy.load()
    date_filter = Q()
    if start:
        date_filter &= Q(attendance__date__gte=start)
    if end:
        date_filter &= Q(attendance__date__lte=end)
    pct = ExpressionWrapper(
        F("att_present") * Decimal("100.0") / F("att_total"),
        output_field=DecimalField(max_digits=6, decimal_places=2),
    )
    return (
        student_qs.annotate(
            att_total=Count("attendance", filter=Q(date_filter)),
            att_present=Count("attendance", filter=numerator_q(policy) & date_filter),
        )
        .annotate(
            attendance_pct=Case(
                When(att_total=0, then=Value(None)),
                default=pct,
                output_field=DecimalField(max_digits=6, decimal_places=2),
            )
        )
        .order_by("pk")
    )


def attendance_list_qs(
    *,
    user: "UserType",
    q: str | None = None,
    group_id: int | None = None,
    status: str | None = None,
    on_date: date | None = None,
    start: date | None = None,
    end: date | None = None,
) -> QuerySet[Attendance]:
    from common.scoping import scoped_queryset

    qs = Attendance.objects.select_related("student__group", "timeslot")
    qs = scoped_queryset(qs, user)
    if q:
        qs = qs.filter(
            Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(student__admission_no__icontains=q)
        )
    if group_id:
        qs = qs.filter(student__group_id=group_id)
    if status:
        qs = qs.filter(status=status)
    if on_date:
        qs = qs.filter(date=on_date)
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)
    return qs.order_by("-date", "student__last_name")


def attendance_recent_qs(student: Student, limit: int = 10) -> QuerySet[Attendance]:
    return (
        Attendance.objects.filter(student=student)
        .select_related("timeslot")
        .order_by("-date")[:limit]
    )


def attendance_counts_for_date(*, user: "UserType", on_date: date) -> dict[str, int]:
    """Per-status counts scoped to the user's boundary (dashboards)."""
    from common.scoping import scoped_queryset

    qs = Attendance.objects.filter(date=on_date)
    qs = scoped_queryset(qs, user)
    rows = qs.values("status").annotate(total=Count("pk"))
    counters = {status: 0 for status in Attendance.Status.values}
    for row in rows:
        counters[row["status"]] = row["total"]
    return counters


def attendance_trend(*, user: "UserType", days: int = 14) -> list[dict[str, Any]]:
    """Daily [date, percent, marked] pairs for charts, scoped to the boundary."""
    from django.utils import timezone

    from common.scoping import scoped_queryset

    start_date = timezone.localdate() - timezone.timedelta(days=days - 1)
    qs = Attendance.objects.filter(date__gte=start_date)
    qs = scoped_queryset(qs, user)
    policy = Policy.load()
    counted = numerator_q(policy, prefix="")
    rows = (
        qs.values("date")
        .annotate(
            total=Count("pk"),
            present=Count("pk", filter=counted),
        )
        .order_by("date")
    )
    trend = []
    for row in rows:
        percentage = (
            round(Decimal(row["present"]) / Decimal(row["total"]) * 100, 1)
            if row["total"]
            else None
        )
        trend.append({"date": row["date"], "percent": percentage, "marked": row["total"]})
    return trend


def fmt_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))
