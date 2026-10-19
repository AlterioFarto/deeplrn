"""Shared pytest fixtures: role users inside their authorization boundaries."""

from decimal import Decimal

import pytest

from academics.factories import GroupFactory
from accounts.factories import AdminUserFactory, GuardianUserFactory, MentorUserFactory
from attendance.factories import AttendanceFactory
from billing.factories import InvoiceFactory
from common.roles import Role
from common.scoping import get_boundary, scoped_queryset
from students.factories import StudentFactory
from students.models import GuardianLink


@pytest.fixture
def admin(db):
    return AdminUserFactory()


@pytest.fixture
def admin_client(client, admin):
    client.force_login(admin)
    return client


@pytest.fixture
def mentor(db):
    return MentorUserFactory()


@pytest.fixture
def mentor_profile(mentor):
    return mentor.mentor_profile


@pytest.fixture
def mentor_client(client, mentor):
    client.force_login(mentor)
    return client


@pytest.fixture
def guardian(db):
    return GuardianUserFactory()


@pytest.fixture
def guardian_client(client, guardian):
    client.force_login(guardian)
    return client


@pytest.fixture
def group():
    return GroupFactory()


@pytest.fixture
def mentor_group(mentor, group):
    """Mentor assigned to the group: their authorization boundary."""
    mentor.mentor_profile.groups.add(group)
    return group


@pytest.fixture
def student(mentor_group):
    return StudentFactory(group=mentor_group)


@pytest.fixture
def guardian_student(guardian, group):
    """Guardian-linked student: their authorization boundary."""
    student = StudentFactory(group=group)
    GuardianLink.objects.create(student=student, guardian=guardian.guardian_profile)
    return student


@pytest.fixture
def student_client(client, student, guardian):
    from accounts.factories import GuardianProfileFactory  # noqa: F401

    client.force_login(guardian)
    return client


@pytest.fixture
def attendance(student, admin):
    return AttendanceFactory(student=student, status="PRESENT")


@pytest.fixture
def invoice(student):
    return InvoiceFactory(student=student, amount_due=Decimal("500.00"), status="ISSUED")


@pytest.mark.django_db
class TestRoleBoundary:
    def test_mentor_sees_only_assigned_group_students(self, mentor, mentor_group):
        mine = StudentFactory(group=mentor_group)
        other = StudentFactory(group=GroupFactory(name="Other Group"))
        ids = set(get_boundary(mentor).students_qs().values_list("pk", flat=True))
        assert mine.pk in ids
        assert other.pk not in ids

    def test_guardian_sees_only_linked_students(self, guardian, guardian_student):
        other = StudentFactory(group=GroupFactory(name="Unlinked Group"))
        ids = set(get_boundary(guardian).students_qs().values_list("pk", flat=True))
        assert guardian_student.pk in ids
        assert other.pk not in ids

    def test_unknown_model_shape_fails_closed(self, guardian):
        from accounts.models import User

        assert not scoped_queryset(User.objects.all(), guardian).exists()

    def test_role_values(self, admin):
        assert Role(admin.role) == Role.ADMIN

    def test_group_ids_none_for_admin(self, admin):
        assert get_boundary(admin).group_ids() is None
