"""Result read paths: scoped lists and per-student summaries."""

from typing import TYPE_CHECKING

from django.db.models import Q, QuerySet

from common.scoping import scoped_queryset
from results.models import Result

if TYPE_CHECKING:
    from accounts.models import User as UserType
    from students.models import Student


def result_list_qs(
    *, user: "UserType", exam_id: int | None = None, q: str | None = None
) -> QuerySet[Result]:
    qs = Result.objects.select_related("student__group", "exam__subject", "exam__group")
    qs = scoped_queryset(qs, user)
    if exam_id:
        qs = qs.filter(exam_id=exam_id)
    if q:
        qs = qs.filter(
            Q(student__first_name__icontains=q)
            | Q(student__last_name__icontains=q)
            | Q(student__admission_no__icontains=q)
        )
    return qs.order_by("-exam__date", "student__last_name", "student__first_name")


def results_for_exam(*, user: "UserType", exam: "object") -> QuerySet[Result]:
    qs = Result.objects.filter(exam=exam).select_related("student")
    return scoped_queryset(qs, user).order_by("student__admission_no")


def result_recent_qs(student: "Student", limit: int = 10) -> QuerySet[Result]:
    return (
        Result.objects.filter(student=student)
        .select_related("exam__subject")
        .order_by("-exam__date")[:limit]
    )
