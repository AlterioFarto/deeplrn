"""Student and guardian read paths: scoped, annotated, N+1-free."""

from typing import TYPE_CHECKING

from django.db.models import Count, Prefetch, Q, QuerySet

from common.scoping import scoped_queryset
from students.models import Enrollment, GuardianLink, Student

if TYPE_CHECKING:
    from accounts.models import User as UserType


def student_list_qs(
    *,
    user: "UserType",
    q: str | None = None,
    group_id: int | None = None,
    status: str | None = None,
) -> QuerySet[Student]:
    qs = Student.objects.select_related("group").annotate(
        guardian_count=Count("guardian_links", distinct=True),
        open_invoice_count=Count(
            "invoices",
            filter=Q(invoices__status="ISSUED"),
            distinct=True,
        ),
    )
    qs = scoped_queryset(qs, user)
    if q:
        qs = qs.filter(
            Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(admission_no__icontains=q)
        )
    if group_id:
        qs = qs.filter(group_id=group_id)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)
    return qs


def student_detail_qs(*, user: "UserType") -> QuerySet[Student]:
    qs = Student.objects.select_related("group").prefetch_related(
        Prefetch(
            "guardian_links",
            queryset=GuardianLink.objects.select_related("guardian__user").order_by(
                "-is_primary_contact"
            ),
        ),
        "enrollments__group",
    )
    return scoped_queryset(qs, user)


def guardian_list_qs(*, user: "UserType", q: str | None = None) -> QuerySet:
    from accounts import selectors

    return selectors.guardian_list_qs(user=user, q=q)


def visible_groups_for_form(user: "UserType") -> QuerySet:
    from academics.selectors import visible_groups_for_form as _groups

    return _groups(user)


def enrollments_for_student(student: Student) -> QuerySet[Enrollment]:
    return student.enrollments.select_related("group").order_by("-enrolled_on")
