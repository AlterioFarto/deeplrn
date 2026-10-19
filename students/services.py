"""Student, guardian and enrollment mutations. Transactional and audited."""

from datetime import date

from django.db import IntegrityError, transaction
from django.utils import timezone

from academics.models import Group
from accounts.models import GuardianProfile, User
from common.audit import log_action, make_diff, snapshot
from common.exceptions import AuthorizationError, ConflictError
from common.roles import Role
from common.scoping import assert_can_access, assert_can_manage_group
from students.models import Enrollment, GuardianLink, Student


def _assert_group_capacity(group: Group) -> None:
    active_count = group.students.filter(deleted_at__isnull=True, is_active=True).count()
    if active_count >= group.capacity:
        raise ConflictError(f"Group “{group.name}” is at capacity ({group.capacity}).")


@transaction.atomic
def create_student(
    *,
    group: Group,
    first_name: str,
    last_name: str,
    admission_no: str,
    dob: date | None,
    enrollment_date: date,
    is_active: bool = True,
    actor: User | None = None,
) -> Student:
    assert_can_manage_group(actor, group)
    _assert_group_capacity(group)
    student = Student.objects.create(
        group=group,
        first_name=first_name,
        last_name=last_name,
        admission_no=admission_no.strip(),
        dob=dob,
        enrollment_date=enrollment_date,
        is_active=is_active,
    )
    Enrollment.objects.create(
        student=student,
        group=group,
        academic_year=group.academic_year,
        enrolled_on=enrollment_date,
    )
    log_action(actor=actor, action="create", obj=student)
    return student


@transaction.atomic
def update_student(
    *,
    student: Student,
    group: Group,
    first_name: str,
    last_name: str,
    admission_no: str,
    dob: date | None,
    enrollment_date: date,
    is_active: bool,
    actor: User | None = None,
) -> Student:
    assert_can_access(actor, student)
    assert_can_manage_group(actor, group)
    if group_id_changed := (student.group_id != group.pk):
        _assert_group_capacity(group)
    before = snapshot(
        student, ("group_id", "first_name", "last_name", "admission_no", "dob", "is_active")
    )
    student.group = group
    student.first_name = first_name
    student.last_name = last_name
    student.admission_no = admission_no.strip()
    student.dob = dob
    student.enrollment_date = enrollment_date
    student.is_active = is_active
    student.save()
    if group_id_changed:
        _close_open_enrollment(student)
        Enrollment.objects.create(
            student=student,
            group=group,
            academic_year=group.academic_year,
            enrolled_on=timezone.localdate(),
        )
    log_action(
        actor=actor,
        action="update",
        obj=student,
        diff=make_diff(
            before, student, ("group_id", "first_name", "last_name", "admission_no", "is_active")
        ),
    )
    return student


def _close_open_enrollment(student: Student) -> None:
    Enrollment.objects.filter(student=student, left_on__isnull=True).update(
        left_on=timezone.localdate()
    )


@transaction.atomic
def deactivate_student(*, student: Student, actor: User | None = None) -> Student:
    assert_can_access(actor, student)
    before = snapshot(student, ("is_active",))
    student.is_active = False
    student.save(update_fields=["is_active", "updated_at"])
    student.delete()
    _close_open_enrollment(student)
    log_action(
        actor=actor,
        action="soft_delete",
        obj=student,
        diff=make_diff(before, student, ("is_active",)),
    )
    return student


@transaction.atomic
def restore_student(*, student: Student, actor: User | None = None) -> Student:
    if actor is None or actor.role != Role.ADMIN:
        raise AuthorizationError("Only admins can restore students.")
    student.restore()
    student.is_active = True
    student.save(update_fields=["is_active", "updated_at"])
    log_action(actor=actor, action="restore", obj=student)
    return student


@transaction.atomic
def link_guardian(
    *,
    student: Student,
    guardian: GuardianProfile,
    relationship: str,
    is_primary_contact: bool,
    actor: User | None = None,
) -> GuardianLink:
    assert_can_access(actor, student)
    if guardian.deleted_at or not guardian.user.is_active:
        raise ConflictError("This guardian account is not available.")
    has_primary = GuardianLink.objects.filter(student=student, is_primary_contact=True).exists()
    if is_primary_contact:
        GuardianLink.objects.filter(student=student, is_primary_contact=True).update(
            is_primary_contact=False
        )
    try:
        link = GuardianLink.objects.create(
            student=student,
            guardian=guardian,
            relationship=relationship,
            is_primary_contact=is_primary_contact or not has_primary,
        )
    except IntegrityError as exc:
        raise ConflictError("This guardian is already linked to the student.") from exc
    log_action(actor=actor, action="create", obj=link)
    return link


@transaction.atomic
def unlink_guardian(*, link: GuardianLink, actor: User | None = None) -> None:
    assert_can_access(actor, link.student)
    was_primary = link.is_primary_contact
    log_action(actor=actor, action="soft_delete", obj=link)
    link.delete()
    if was_primary:
        remaining = GuardianLink.objects.filter(student=link.student).order_by("pk").first()
        if remaining:
            remaining.is_primary_contact = True
            remaining.save(update_fields=["is_primary_contact"])


@transaction.atomic
def enroll_student(*, student: Student, group: Group, actor: User | None = None) -> Student:
    """Move a student to another group, recording the enrollment history."""
    assert_can_access(actor, student)
    assert_can_manage_group(actor, group)
    if student.group_id == group.pk:
        return student
    _assert_group_capacity(group)
    _close_open_enrollment(student)
    Enrollment.objects.create(
        student=student,
        group=group,
        academic_year=group.academic_year,
        enrolled_on=timezone.localdate(),
    )
    student.group = group
    student.save(update_fields=["group", "updated_at"])
    log_action(actor=actor, action="update", obj=student, diff={"group": ["", group.name]})
    return student
