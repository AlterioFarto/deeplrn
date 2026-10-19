"""Dashboard read models: role-scoped, annotated, cached aggregates.

Cached values are plain JSON-able dicts; querysets never go into the cache.
"""

from decimal import Decimal
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, Q
from django.utils import timezone

from academics.models import Exam, Group
from accounts.models import GuardianProfile, MentorProfile, User
from attendance.models import Policy
from attendance.selectors import (
    annotate_attendance,
    attendance_counts_for_date,
    attendance_trend,
    numerator_q,
)
from billing import selectors as billing_selectors
from billing.models import Invoice
from common.roles import Role
from common.scoping import get_boundary, scoped_queryset
from dashboard.caching import key_for
from students.models import Student

TREND_DAYS = 14


def _upcoming_exams(user: User, limit: int = 6) -> list[dict[str, Any]]:
    today = timezone.localdate()
    exams = scoped_queryset(
        Exam.objects.filter(date__gte=today).select_related("group", "subject"), user
    ).order_by("date", "start_time")[:limit]
    return [
        {
            "id": exam.pk,
            "subject": exam.subject.name,
            "group": exam.group.name,
            "date": exam.date.isoformat(),
            "start_time": exam.start_time.strftime("%H:%M"),
            "max_marks": exam.max_marks,
        }
        for exam in exams
    ]


def _pct(present: int, total: int) -> str | None:
    if not total:
        return None
    return f"{present / total * 100:.1f}"


def admin_stats(user: User) -> dict[str, Any]:
    today = timezone.localdate()
    students_qs = Student.objects.filter(deleted_at__isnull=True, is_active=True)
    at_risk = (
        annotate_attendance(students_qs)
        .filter(attendance_pct__lt=settings.ATTENDANCE_RISK_THRESHOLD)
        .order_by("attendance_pct")
        .select_related("group")[:5]
    )
    counts = attendance_counts_for_date(user=user, on_date=today)
    return {
        "student_count": students_qs.count(),
        "group_count": Group.objects.filter(is_active=True).count(),
        "mentor_count": MentorProfile.objects.filter(deleted_at__isnull=True).count(),
        "guardian_count": GuardianProfile.objects.filter(deleted_at__isnull=True).count(),
        "outstanding_total": str(billing_selectors.outstanding_total(user=user)),
        "collected_this_month": str(
            billing_selectors.paid_total(start=today.replace(day=1), end=today)
        ),
        "attendance_today": counts,
        "upcoming_exams": _upcoming_exams(user),
        "trend": attendance_trend(user=user, days=TREND_DAYS),
        "at_risk": [
            {
                "id": student.pk,
                "name": student.full_name,
                "group": student.group.name,
                "percent": (
                    str(student.attendance_pct) if student.attendance_pct is not None else None
                ),
            }
            for student in at_risk
        ],
        "threshold": settings.ATTENDANCE_RISK_THRESHOLD,
    }


def mentor_stats(user: User) -> dict[str, Any]:
    boundary = get_boundary(user)
    group_ids = boundary.group_ids() or set()
    policy = Policy.load()
    groups = (
        Group.objects.filter(pk__in=group_ids)
        .annotate(
            student_count=Count(
                "students", filter=Q(students__deleted_at__isnull=True, students__is_active=True)
            ),
            att_total=Count("students__attendance", filter=Q(students__deleted_at__isnull=True)),
            att_present=Count(
                "students__attendance",
                filter=numerator_q(policy, prefix="students__attendance")
                & Q(students__deleted_at__isnull=True),
            ),
        )
        .order_by("name")
    )
    return {
        "group_count": groups.count(),
        "student_count": Student.objects.filter(
            group_id__in=group_ids, deleted_at__isnull=True, is_active=True
        ).count(),
        "groups": [
            {
                "id": group.pk,
                "name": group.name,
                "student_count": group.student_count,
                "percent": _pct(group.att_present, group.att_total),
            }
            for group in groups
        ],
        "attendance_today": attendance_counts_for_date(user=user, on_date=timezone.localdate()),
        "upcoming_exams": _upcoming_exams(user),
        "trend": attendance_trend(user=user, days=TREND_DAYS),
    }


def guardian_stats(user: User) -> dict[str, Any]:
    boundary = get_boundary(user)
    students = annotate_attendance(
        boundary.students_qs().filter(is_active=True).select_related("group").order_by("first_name")
    )
    invoices = (
        billing_selectors.invoice_list_qs(user=user)
        .filter(status=Invoice.Status.ISSUED)
        .values("student_id", "outstanding")
    )
    outstanding_by_student: dict[int, Decimal] = {}
    for row in invoices:
        outstanding_by_student[row["student_id"]] = outstanding_by_student.get(
            row["student_id"], Decimal(0)
        ) + Decimal(row["outstanding"])
    return {
        "students": [
            {
                "id": student.pk,
                "name": student.full_name,
                "group": student.group.name,
                "percent": (
                    str(student.attendance_pct) if student.attendance_pct is not None else None
                ),
                "outstanding": str(outstanding_by_student.get(student.pk, Decimal("0.00"))),
            }
            for student in students
        ],
        "attendance_today": attendance_counts_for_date(user=user, on_date=timezone.localdate()),
        "upcoming_exams": _upcoming_exams(user),
        "trend": attendance_trend(user=user, days=TREND_DAYS),
    }


def cached_stats(user: User) -> dict[str, Any]:
    """Dashboard aggregates with versioned cache and short TTL."""
    key = key_for(user.pk)
    data = cache.get(key)
    if data is None:
        data = _build(user)
        cache.set(key, data, getattr(settings, "CACHE_TTL", 60))
    return data


def _build(user: User) -> dict[str, Any]:
    role = Role(user.role)
    if role == Role.MENTOR:
        return mentor_stats(user)
    if role == Role.GUARDIAN:
        return guardian_stats(user)
    return admin_stats(user)
