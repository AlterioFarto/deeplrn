"""Academic read paths: scoped, annotated, N+1-free."""

from typing import TYPE_CHECKING

from django.db.models import Count, Q, QuerySet
from django.utils import timezone

from academics.models import Exam, Group, Schedule, Subject, TimeSlot
from common.scoping import get_boundary, scoped_queryset

if TYPE_CHECKING:
    from accounts.models import User as UserType


def group_list_qs(*, user: "UserType", q: str | None = None) -> QuerySet[Group]:
    qs = (
        Group.objects.annotate(
            student_count=Count(
                "students", filter=Q(students__deleted_at__isnull=True), distinct=True
            ),
            mentor_count=Count("assigned_mentors", distinct=True),
        )
        .select_related()
        .order_by("name")
    )
    qs = scoped_queryset(qs, user)
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(academic_year__icontains=q)
    return qs


def group_detail_qs(*, user: "UserType") -> QuerySet[Group]:
    qs = Group.objects.prefetch_related(
        "assigned_mentors__user",
        "schedules__subject",
        "schedules__timeslot",
    )
    return scoped_queryset(qs, user)


def subject_list_qs(*, q: str | None = None) -> QuerySet[Subject]:
    qs = Subject.objects.annotate(exam_count=Count("exams", distinct=True)).order_by("name")
    if q:
        qs = qs.filter(name__icontains=q) | qs.filter(code__icontains=q)
    return qs


def timeslot_list_qs(*, q: str | None = None) -> QuerySet[TimeSlot]:
    qs = TimeSlot.objects.annotate(schedule_count=Count("schedules", distinct=True)).order_by(
        "start_time"
    )
    if q:
        qs = qs.filter(name__icontains=q)
    return qs


def schedule_list_qs(
    *, user: "UserType", group_id: int | None = None, day: int | None = None
) -> QuerySet[Schedule]:
    qs = Schedule.objects.select_related("group", "subject", "mentor", "timeslot")
    qs = scoped_queryset(qs, user)
    if group_id:
        qs = qs.filter(group_id=group_id)
    if day is not None and day != "":
        qs = qs.filter(day=int(day))
    return qs


def exam_list_qs(
    *, user: "UserType", group_id: int | None = None, upcoming_only: bool = False
) -> QuerySet[Exam]:
    today = timezone.localdate()
    qs = Exam.objects.select_related("group", "subject").annotate(
        result_count=Count("results", distinct=True)
    )
    qs = scoped_queryset(qs, user)
    if group_id:
        qs = qs.filter(group_id=group_id)
    if upcoming_only:
        qs = qs.filter(date__gte=today)
    return qs


def mentor_can_teach_group(*, mentor: "UserType", group: Group) -> bool:
    profile = getattr(mentor, "mentor_profile", None)
    return bool(profile and profile.pk and profile.groups.filter(pk=group.pk).exists())


def visible_groups_for_form(user: "UserType") -> QuerySet[Group]:
    boundary = get_boundary(user)
    qs = Group.objects.filter(is_active=True).order_by("name")
    return boundary.restrict_group_pk(qs)
