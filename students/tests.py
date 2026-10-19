"""Students domain tests: capacity, soft delete/restore, guardian links."""

import pytest
from django.db import IntegrityError

from academics.factories import GroupFactory
from common.exceptions import ConflictError
from students import services
from students.models import GuardianLink

pytestmark = pytest.mark.django_db


def _create(group, no="S0001", first="Amy", actor=None):
    return services.create_student(
        group=group,
        first_name=first,
        last_name="Bell",
        admission_no=no,
        dob=None,
        enrollment_date="2025-01-10",
        is_active=True,
        actor=actor,
    )


def test_capacity_enforced(admin):
    group = GroupFactory(name="Cap Test", capacity=3)
    for number in range(3):
        _create(group, no=f"S{number:04d}", actor=admin)
    with pytest.raises(ConflictError):
        _create(group, no="S0400", actor=admin)


def test_unique_admission_among_alive(mentor_group, admin):
    _create(mentor_group, no="S1001", actor=admin)
    with pytest.raises(IntegrityError):
        services.create_student(
            group=mentor_group,
            first_name="Zoe",
            last_name="Clone",
            admission_no="S1001",
            dob=None,
            enrollment_date="2025-01-10",
            is_active=True,
            actor=admin,
        )


def test_soft_delete_then_reuse_admission(mentor_group, admin):
    student = _create(mentor_group, no="S2001", actor=admin)
    services.deactivate_student(student=student, actor=admin)
    student.refresh_from_db()
    assert student.deleted_at is not None
    reused = _create(mentor_group, no="S2001", first="Bob", actor=admin)
    assert reused.pk != student.pk


def test_restore_student(mentor_group, admin):
    student = _create(mentor_group, no="S3001", actor=admin)
    student.delete()
    services.restore_student(student=student, actor=admin)
    student.refresh_from_db()
    assert student.deleted_at is None
    assert student.is_active is True


def test_guardian_link_unique(mentor_group, guardian, admin):
    student = _create(mentor_group, no="S6001", actor=admin)
    services.link_guardian(
        student=student,
        guardian=guardian.guardian_profile,
        relationship="MOTHER",
        is_primary_contact=True,
        actor=admin,
    )
    with pytest.raises(ConflictError):
        services.link_guardian(
            student=student,
            guardian=guardian.guardian_profile,
            relationship="FATHER",
            is_primary_contact=False,
            actor=admin,
        )
    assert GuardianLink.objects.filter(student=student).count() == 1


def test_primary_contact_unique_per_student(mentor_group, guardian, admin):
    student = _create(mentor_group, no="S7001", actor=admin)
    services.link_guardian(
        student=student,
        guardian=guardian.guardian_profile,
        relationship="MOTHER",
        is_primary_contact=True,
        actor=admin,
    )
    other = _create(mentor_group, no="S7002", first="Bob", actor=admin)
    services.link_guardian(
        student=other,
        guardian=guardian.guardian_profile,
        relationship="FATHER",
        is_primary_contact=True,
        actor=admin,
    )
    assert GuardianLink.objects.filter(guardian=guardian.guardian_profile).count() == 2
