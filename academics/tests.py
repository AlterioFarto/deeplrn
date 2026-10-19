"""Academics domain tests: constraints and conflict detection."""

import pytest
from django.db import IntegrityError

from academics import services
from academics.factories import GroupFactory, ScheduleFactory, SubjectFactory
from academics.models import Schedule
from common.exceptions import ConflictError

pytestmark = pytest.mark.django_db


def test_schedule_group_slot_unique(db):
    first = ScheduleFactory()
    with pytest.raises(IntegrityError):
        Schedule.objects.create(
            group=first.group,
            subject=SubjectFactory(),
            mentor=first.mentor,
            timeslot=first.timeslot,
            day=first.day,
        )


def test_schedule_mentor_slot_unique(db):
    first = ScheduleFactory()
    other_group = GroupFactory(name="Collision Group")
    with pytest.raises(IntegrityError):
        Schedule.objects.create(
            group=other_group,
            subject=first.subject,
            mentor=first.mentor,
            timeslot=first.timeslot,
            day=first.day,
        )


def test_create_timeslot_rejects_reversed_range(admin):
    with pytest.raises(ConflictError):
        services.create_timeslot(name="Reversed", start_time="10:00", end_time="09:00", actor=admin)


def test_create_exam_rejects_zero_max_marks(admin, mentor_group):
    with pytest.raises(ConflictError):
        services.create_exam(
            subject=SubjectFactory(),
            group=mentor_group,
            date="2025-11-01",
            start_time="09:00",
            duration_minutes=60,
            max_marks=0,
            created_by=admin,
            actor=admin,
        )
