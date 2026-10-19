"""Accounts domain tests: profile reconciliation and role changes."""

import pytest
from django.urls import reverse

from accounts import services
from accounts.models import GuardianProfile, MentorProfile
from common.roles import Role

pytestmark = pytest.mark.django_db


def test_login_post_flow(client, admin):
    """The real login form (not force_login) authenticates and redirects."""
    admin.set_password("Passw0rd-not-common-9")
    admin.save()
    response = client.post(
        reverse("accounts:login"),
        {"email": admin.email, "password": "Passw0rd-not-common-9"},
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("dashboard:home")
    assert response.wsgi_request.user.is_authenticated


def test_login_wrong_password_renders_form(client, admin):
    admin.set_password("Passw0rd-not-common-9")
    admin.save()
    response = client.post(
        reverse("accounts:login"),
        {"email": admin.email, "password": "definitely-wrong"},
    )
    assert response.status_code == 200
    assert response.wsgi_request.user.is_anonymous


def test_create_user_creates_role_profile(admin):
    user = services.create_user(
        email="new-mentor@x.test",
        first_name="New",
        last_name="Mentor",
        role=Role.MENTOR.value,
        password="Passw0rd-very-strong-2",
        actor=admin,
    )
    assert MentorProfile.objects.filter(user=user).exists()
    assert GuardianProfile.objects.filter(user=user).exists() is False


def test_role_change_reconciles_profiles(admin):
    user = services.create_user(
        email="switch@x.test",
        first_name="Sky",
        last_name="Switch",
        role=Role.MENTOR.value,
        password="Passw0rd-very-strong-2",
        actor=admin,
    )
    services.set_user_role(user=user, role=Role.GUARDIAN.value, actor=admin)
    profile = GuardianProfile.objects.get(user=user)
    assert MentorProfile.all_objects.filter(user=user, deleted_at__isnull=False).exists()
    assert profile.deleted_at is None


def test_deactivate_detaches_group_assignments(admin, mentor_group):
    mentor = mentor_group.assigned_mentors.first().user
    services.deactivate_user(user=mentor, actor=admin)
    mentor.refresh_from_db()
    assert mentor.is_active is False
    assert mentor.mentor_profile.groups.count() == 0


def test_password_hint_generation(admin):
    hint = services.generate_password_hint()
    assert 8 <= len(hint) <= 24
