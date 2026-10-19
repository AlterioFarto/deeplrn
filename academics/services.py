"""Academic mutations. All writes are transactional, guarded and audited."""

from datetime import date

from django.db import transaction

from academics.models import Exam, Group, Schedule, Subject, TimeSlot
from accounts.models import MentorProfile, User
from common.audit import log_action, make_diff, snapshot
from common.exceptions import AuthorizationError, ConflictError
from common.roles import Role
from common.scoping import assert_can_manage_group


# -- Groups -----------------------------------------------------------------
@transaction.atomic
def create_group(
    *,
    name: str,
    academic_year: str,
    capacity: int,
    is_active: bool = True,
    actor: User | None = None,
) -> Group:
    group = Group.objects.create(
        name=name, academic_year=academic_year, capacity=capacity, is_active=is_active
    )
    log_action(actor=actor, action="create", obj=group)
    return group


@transaction.atomic
def update_group(
    *,
    group: Group,
    name: str,
    academic_year: str,
    capacity: int,
    is_active: bool,
    actor: User | None = None,
) -> Group:
    assert_can_manage_group(actor, group)
    fields = ("name", "academic_year", "capacity", "is_active")
    before = snapshot(group, fields)
    group.name = name
    group.academic_year = academic_year
    group.capacity = capacity
    group.is_active = is_active
    group.save()
    log_action(actor=actor, action="update", obj=group, diff=make_diff(before, group, fields))
    return group


@transaction.atomic
def delete_group(*, group: Group, actor: User | None = None) -> None:
    if actor is None or actor.role != Role.ADMIN:
        raise AuthorizationError("Only admins can delete groups.")
    if group.students.filter(deleted_at__isnull=True).exists():
        raise ConflictError("This group still has students. Move them to another group first.")
    if group.schedules.exists():
        raise ConflictError("This group still has timetable entries. Remove them first.")
    log_action(actor=actor, action="soft_delete", obj=group)
    group.delete()


# -- Subjects ----------------------------------------------------------------
@transaction.atomic
def create_subject(*, name: str, code: str, actor: User | None = None) -> Subject:
    subject = Subject.objects.create(name=name, code=code)
    log_action(actor=actor, action="create", obj=subject)
    return subject


@transaction.atomic
def update_subject(*, subject: Subject, name: str, code: str, actor: User | None = None) -> Subject:
    before = snapshot(subject, ("name", "code"))
    subject.name = name
    subject.code = code
    subject.save()
    log_action(
        actor=actor, action="update", obj=subject, diff=make_diff(before, subject, ("name", "code"))
    )
    return subject


@transaction.atomic
def delete_subject(*, subject: Subject, actor: User | None = None) -> None:
    if actor is None or actor.role != Role.ADMIN:
        raise AuthorizationError("Only admins can delete subjects.")
    if subject.exams.exists() or subject.schedules.exists():
        raise ConflictError("This subject is used by exams or the timetable and cannot be deleted.")
    log_action(actor=actor, action="soft_delete", obj=subject)
    subject.delete()


# -- Time slots ----------------------------------------------------------------
@transaction.atomic
def create_timeslot(*, name: str, start_time, end_time, actor: User | None = None) -> TimeSlot:
    if end_time <= start_time:
        raise ConflictError("End time must be after start time.")
    timeslot = TimeSlot.objects.create(name=name, start_time=start_time, end_time=end_time)
    log_action(actor=actor, action="create", obj=timeslot)
    return timeslot


@transaction.atomic
def update_timeslot(
    *, timeslot: TimeSlot, name: str, start_time, end_time, actor: User | None = None
) -> TimeSlot:
    if end_time <= start_time:
        raise ConflictError("End time must be after start time.")
    before = snapshot(timeslot, ("name", "start_time", "end_time"))
    timeslot.name = name
    timeslot.start_time = start_time
    timeslot.end_time = end_time
    timeslot.save()
    log_action(
        actor=actor,
        action="update",
        obj=timeslot,
        diff=make_diff(before, timeslot, ("name", "start_time", "end_time")),
    )
    return timeslot


@transaction.atomic
def delete_timeslot(*, timeslot: TimeSlot, actor: User | None = None) -> None:
    if actor is None or actor.role != Role.ADMIN:
        raise AuthorizationError("Only admins can delete time slots.")
    if timeslot.schedules.exists() or timeslot.attendance_set.exists():
        raise ConflictError(
            "This time slot is used by the timetable or attendance and cannot be deleted."
        )
    log_action(actor=actor, action="soft_delete", obj=timeslot)
    timeslot.delete()


# -- Schedule ----------------------------------------------------------------
def _validated_mentor_group(mentor: User, group: Group) -> None:
    if mentor.role != Role.MENTOR:
        raise AuthorizationError("The selected user is not a mentor.")
    profile = MentorProfile.all_objects.filter(user=mentor).first()
    if profile is None or profile.deleted_at:
        raise AuthorizationError("The selected mentor has no mentor profile.")
    if not profile.groups.filter(pk=group.pk).exists():
        raise AuthorizationError("This mentor is not assigned to this group.")


@transaction.atomic
def create_schedule(
    *,
    group: Group,
    subject: Subject,
    mentor: User,
    timeslot: TimeSlot,
    day: int,
    actor: User | None = None,
) -> Schedule:
    assert_can_manage_group(actor, group)
    _validated_mentor_group(mentor, group)
    schedule = Schedule.objects.create(
        group=group, subject=subject, mentor=mentor, timeslot=timeslot, day=day
    )
    log_action(actor=actor, action="create", obj=schedule)
    return schedule


@transaction.atomic
def update_schedule(
    *,
    schedule: Schedule,
    group: Group,
    subject: Subject,
    mentor: User,
    timeslot: TimeSlot,
    day: int,
    actor: User | None = None,
) -> Schedule:
    assert_can_manage_group(actor, schedule.group)
    assert_can_manage_group(actor, group)
    _validated_mentor_group(mentor, group)
    fields = ("group_id", "subject_id", "mentor_id", "timeslot_id", "day")
    before = snapshot(schedule, fields)
    schedule.group = group
    schedule.subject = subject
    schedule.mentor = mentor
    schedule.timeslot = timeslot
    schedule.day = day
    schedule.save()
    log_action(actor=actor, action="update", obj=schedule, diff=make_diff(before, schedule, fields))
    return schedule


@transaction.atomic
def delete_schedule(*, schedule: Schedule, actor: User | None = None) -> None:
    assert_can_manage_group(actor, schedule.group)
    log_action(actor=actor, action="soft_delete", obj=schedule)
    schedule.delete()


# -- Exams ----------------------------------------------------------------
def _validated_exam_fields(max_marks: int, duration_minutes: int) -> None:
    if max_marks <= 0:
        raise ConflictError("Maximum marks must be greater than zero.")
    if not 0 < duration_minutes <= 600:
        raise ConflictError("Duration must be between 1 and 600 minutes.")


@transaction.atomic
def create_exam(
    *,
    subject: Subject,
    group: Group,
    date: date,
    start_time,
    duration_minutes: int,
    max_marks: int,
    created_by: User | None,
    actor: User | None = None,
) -> Exam:
    assert_can_manage_group(actor, group)
    _validated_exam_fields(max_marks, duration_minutes)
    exam = Exam.objects.create(
        subject=subject,
        group=group,
        date=date,
        start_time=start_time,
        duration_minutes=duration_minutes,
        max_marks=max_marks,
        created_by=created_by,
    )
    log_action(actor=actor, action="create", obj=exam)
    return exam


@transaction.atomic
def update_exam(
    *,
    exam: Exam,
    subject: Subject,
    group: Group,
    date: date,
    start_time,
    duration_minutes: int,
    max_marks: int,
    actor: User | None = None,
) -> Exam:
    assert_can_manage_group(actor, exam.group)
    assert_can_manage_group(actor, group)
    _validated_exam_fields(max_marks, duration_minutes)
    fields = ("subject_id", "group_id", "date", "start_time", "duration_minutes", "max_marks")
    before = snapshot(exam, fields)
    exam.subject = subject
    exam.group = group
    exam.date = date
    exam.start_time = start_time
    exam.duration_minutes = duration_minutes
    exam.max_marks = max_marks
    exam.save()
    log_action(actor=actor, action="update", obj=exam, diff=make_diff(before, exam, fields))
    return exam


@transaction.atomic
def delete_exam(*, exam: Exam, actor: User | None = None) -> None:
    assert_can_manage_group(actor, exam.group)
    if exam.results.exists():
        raise ConflictError("This exam already has results recorded and cannot be deleted.")
    log_action(actor=actor, action="soft_delete", obj=exam)
    exam.delete()
