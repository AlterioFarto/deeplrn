"""Attendance mutations: single records and idempotent bulk recording."""

from datetime import date

from django.db import transaction
from django.utils import timezone

from academics.models import Group, TimeSlot
from accounts.models import User
from attendance.models import Attendance, Policy
from common.audit import log_action
from common.exceptions import ConflictError
from common.scoping import assert_can_access, assert_can_manage_group
from students.models import Student


def _assert_no_conflicting_records(
    *, student_ids: set[int], on_date: date, timeslot: TimeSlot | None
) -> None:
    if timeslot is None:
        conflict = Attendance.objects.filter(
            student_id__in=student_ids, date=on_date, timeslot__isnull=False
        ).exists()
        if conflict:
            raise ConflictError(
                "Whole-day records conflict with existing per-period records for this date."
            )
    else:
        conflict = Attendance.objects.filter(
            student_id__in=student_ids, date=on_date, timeslot__isnull=True
        ).exists()
        if conflict:
            raise ConflictError(
                "Per-period records conflict with existing whole-day records for this date."
            )


@transaction.atomic
def record_attendance(
    *,
    student: Student,
    on_date: date,
    timeslot: TimeSlot | None,
    status: str,
    recorded_by: User | None,
    notes: str = "",
    actor: User | None = None,
) -> Attendance:
    assert_can_access(actor, student)
    if status not in Attendance.Status.values:
        raise ConflictError("Unknown attendance status.")
    _assert_no_conflicting_records(student_ids={student.pk}, on_date=on_date, timeslot=timeslot)
    attendance, created = Attendance.objects.update_or_create(
        student=student,
        date=on_date,
        timeslot=timeslot,
        defaults={"status": status, "recorded_by": recorded_by, "notes": notes},
    )
    log_action(actor=actor, action="update" if not created else "create", obj=attendance)
    return attendance


@transaction.atomic
def bulk_record_attendance(
    *,
    group: Group,
    on_date: date,
    timeslot: TimeSlot | None,
    statuses: dict[int, str],
    recorded_by: User | None,
    notes: str = "",
    actor: User | None = None,
) -> int:
    """Record attendance for many students atomically and idempotently.

    Re-running with the same input yields the same records (delete-then-create
    within one transaction), so the operation is safe to retry.
    """
    assert_can_manage_group(actor, group)
    if not statuses:
        raise ConflictError("No attendance rows submitted.")
    valid_ids = set(
        Student.objects.filter(group=group, deleted_at__isnull=True).values_list("pk", flat=True)
    )
    unknown = set(statuses) - valid_ids
    if unknown:
        raise ConflictError("Some students do not belong to this group.")
    invalid = set(statuses.values()) - set(Attendance.Status.values)
    if invalid:
        raise ConflictError("Unknown attendance status in submission.")
    _assert_no_conflicting_records(student_ids=set(statuses), on_date=on_date, timeslot=timeslot)

    Attendance.objects.filter(student_id__in=statuses, date=on_date, timeslot=timeslot).delete()
    rows = [
        Attendance(
            student_id=student_id,
            date=on_date,
            timeslot=timeslot,
            status=status,
            recorded_by=recorded_by,
            notes=notes,
        )
        for student_id, status in statuses.items()
    ]
    Attendance.objects.bulk_create(rows, batch_size=500)
    log_action(
        actor=actor,
        action="bulk_attendance",
        diff={
            "group": group.name,
            "date": str(on_date),
            "slot": timeslot.name if timeslot else "whole day",
            "rows": len(rows),
        },
    )
    return len(rows)


def policy() -> Policy:
    return Policy.load()


def today() -> date:
    return timezone.localdate()
