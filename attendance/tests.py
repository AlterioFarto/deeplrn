"""Attendance domain tests: unique constraints, bulk recording, policy."""

import pytest
from django.db import IntegrityError
from django.utils import timezone

from academics.factories import GroupFactory
from attendance import services
from attendance.models import Attendance, Policy
from common.exceptions import ConflictError
from students.factories import StudentFactory

pytestmark = pytest.mark.django_db


def test_unique_slot(student):
    Attendance.objects.create(student=student, status="PRESENT", date=timezone.localdate())
    with pytest.raises(IntegrityError):
        Attendance.objects.create(student=student, status="ABSENT", date=timezone.localdate())


def test_whole_day_only_once(student):
    today = timezone.localdate()
    Attendance.objects.create(student=student, status="PRESENT", date=today, timeslot=None)
    with pytest.raises(IntegrityError):
        Attendance.objects.create(student=student, status="ABSENT", date=today, timeslot=None)


def test_bulk_record_idempotent(student, mentor_group, admin):
    on_date = timezone.localdate()
    services.bulk_record_attendance(
        group=mentor_group,
        on_date=on_date,
        timeslot=None,
        statuses={student.pk: Attendance.Status.PRESENT},
        recorded_by=admin,
        actor=admin,
    )
    services.bulk_record_attendance(
        group=mentor_group,
        on_date=on_date,
        timeslot=None,
        statuses={student.pk: Attendance.Status.LATE},
        recorded_by=admin,
        actor=admin,
    )
    assert Attendance.objects.filter(student=student, date=on_date).count() == 1
    assert (
        Attendance.objects.filter(student=student, date=on_date).get().status
        == Attendance.Status.LATE
    )


def test_bulk_record_rejects_foreign_student(student, mentor_group, admin):
    other = StudentFactory(group=GroupFactory(name="Foreign Group"))
    with pytest.raises(ConflictError):
        services.bulk_record_attendance(
            group=mentor_group,
            on_date=timezone.localdate(),
            timeslot=None,
            statuses={other.pk: Attendance.Status.PRESENT},
            recorded_by=admin,
            actor=admin,
        )


def test_policy_load_is_singleton(db):
    first = Policy.load()
    second = Policy.load()
    assert first.pk == second.pk


def test_num_including_late_respects_policy(student):
    Attendance.objects.create(student=student, status="LATE", date=timezone.localdate())
    policy = Policy.load()
    from attendance.selectors import annotate_attendance

    policy.count_late_as_present = True
    policy.save()
    row = annotate_attendance(type(student).objects.filter(pk=student.pk)).first()
    assert row.attendance_pct == 100.0
    policy.count_late_as_present = False
    policy.save()
    row = annotate_attendance(type(student).objects.filter(pk=student.pk)).first()
    assert row.attendance_pct == 0.0


def test_status_check_constraint(student):
    with pytest.raises(Exception):
        Attendance.objects.create(student=student, status="NOPE", date=timezone.localdate())
