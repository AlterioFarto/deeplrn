"""All account mutations. Every function is transactional and audited."""

from typing import TYPE_CHECKING

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils.crypto import get_random_string

from accounts.models import GroupAssignment, GuardianProfile, MentorProfile, User
from common.audit import log_action, make_diff, snapshot
from common.roles import AuditAction, Role

if TYPE_CHECKING:
    from academics.models import Group

UserModel = get_user_model()


def _mentor_employee_id(user: User) -> str:
    return f"MNT-{user.pk:05d}"


def _profile_for(user: User, role: str) -> tuple[MentorProfile | GuardianProfile | None, bool]:
    """Return (profile, is_mentor_profile) for the given role, or (None, False)."""
    if role != Role.MENTOR.value and role != Role.GUARDIAN.value:
        return None, False
    is_mentor = role == Role.MENTOR.value
    model: type[MentorProfile] | type[GuardianProfile] = (
        MentorProfile if is_mentor else GuardianProfile
    )
    defaults = {"employee_id": _mentor_employee_id(user)} if is_mentor else {}
    profile, created = model.all_objects.get_or_create(user=user, defaults=defaults)
    if not created and profile.deleted_at:
        profile.restore()
    return profile, is_mentor


def _ensure_profile(user: User, role: str) -> None:
    _profile_for(user, role)


def _retire_other_profiles(user: User, role: str) -> None:
    if role != Role.MENTOR.value:
        for mentor_profile in MentorProfile.all_objects.filter(user=user, deleted_at__isnull=True):
            mentor_profile.delete()
    if role != Role.GUARDIAN.value:
        for guardian_profile in GuardianProfile.all_objects.filter(
            user=user, deleted_at__isnull=True
        ):
            guardian_profile.delete()


def _retire_profile_references(user: User, role: str) -> None:
    if role == Role.MENTOR.value:
        mentor_profile = MentorProfile.all_objects.filter(user=user).first()
        if mentor_profile is not None:
            mentor_profile.group_assignments.all().delete()
    if role == Role.GUARDIAN.value:
        guardian_profile = GuardianProfile.all_objects.filter(user=user).first()
        if guardian_profile is not None:
            guardian_profile.student_links.all().delete()


@transaction.atomic
def create_user(
    *,
    email: str,
    first_name: str,
    last_name: str,
    role: str,
    password: str | None = None,
    is_active: bool = True,
    actor: User | None = None,
) -> User:
    """Create a user and their role profile in one transaction."""
    user = UserModel.objects.create_user(
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        role=role,
        is_active=is_active,
    )
    _ensure_profile(user, role)
    log_action(actor=actor, action=AuditAction.CREATE, obj=user)
    return user


@transaction.atomic
def set_user_role(*, user: User, role: str, actor: User | None = None) -> User:
    """Change a user's role and reconcile profiles atomically."""
    before = snapshot(user, ("role",))
    user.role = role
    user.is_staff = role == Role.ADMIN
    user.save(update_fields=["role", "is_staff"])
    _ensure_profile(user, role)
    _retire_other_profiles(user, role)
    _retire_profile_references(user, role)
    log_action(
        actor=actor,
        action=AuditAction.ROLE_CHANGE,
        obj=user,
        diff=make_diff(before, user, ("role",)),
    )
    return user


@transaction.atomic
def deactivate_user(*, user: User, actor: User | None = None) -> User:
    """Deactivate a user, soft-delete their profiles and detach links."""
    before = snapshot(user, ("is_active",))
    user.is_active = False
    user.save(update_fields=["is_active"])
    for mentor_profile in MentorProfile.all_objects.filter(user=user, deleted_at__isnull=True):
        mentor_profile.delete()
    for guardian_profile in GuardianProfile.all_objects.filter(user=user, deleted_at__isnull=True):
        guardian_profile.delete()
    _retire_profile_references(user, user.role)
    log_action(
        actor=actor,
        action=AuditAction.SOFT_DELETE,
        obj=user,
        diff=make_diff(before, user, ("is_active",)),
    )
    return user


@transaction.atomic
def reactivate_user(*, user: User, actor: User | None = None) -> User:
    before = snapshot(user, ("is_active",))
    user.is_active = True
    user.save(update_fields=["is_active"])
    _ensure_profile(user, user.role)
    log_action(
        actor=actor,
        action=AuditAction.RESTORE,
        obj=user,
        diff=make_diff(before, user, ("is_active",)),
    )
    return user


@transaction.atomic
def assign_mentor_to_group(
    *, mentor: User, group: "Group", actor: User | None = None
) -> "GroupAssignment":
    """Attach a MENTOR to a group; this defines their authorization boundary."""
    profile = MentorProfile.all_objects.filter(user=mentor, deleted_at__isnull=True).first()
    if profile is None:
        raise ValueError("Mentor has no active profile; create the MENTOR user first.")
    assignment, _ = GroupAssignment.objects.get_or_create(mentor=profile, group=group)
    if actor is not None:
        log_action(actor=actor, action=AuditAction.ROLE_CHANGE, obj=assignment)
    return assignment


@transaction.atomic
def update_user(
    *,
    user: User,
    actor: User | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    role: str | None = None,
    is_active: bool | None = None,
) -> User:
    """Admin edit of a user; routes through the role/deactivation services."""
    tracked = snapshot(user, ("first_name", "last_name"))
    if first_name is not None:
        user.first_name = first_name
    if last_name is not None:
        user.last_name = last_name
    user.save(update_fields=["first_name", "last_name"])
    log_action(
        actor=actor,
        action=AuditAction.UPDATE,
        obj=user,
        diff=make_diff(tracked, user, ("first_name", "last_name")),
    )
    if role is not None and role != user.role:
        user = set_user_role(user=user, role=role, actor=actor)
    if is_active is False and user.is_active:
        deactivate_user(user=user, actor=actor)
    elif is_active is True and not user.is_active:
        reactivate_user(user=user, actor=actor)
    return user


@transaction.atomic
def update_mentor_profile(
    *, user: User, employee_id: str, specialization_ids: list[int], actor: User | None = None
) -> MentorProfile:
    profile, _ = MentorProfile.all_objects.get_or_create(
        user=user, defaults={"employee_id": employee_id}
    )
    before = snapshot(profile, ("employee_id",))
    profile.employee_id = employee_id
    profile.save(update_fields=["employee_id", "updated_at"])
    profile.specializations.set(specialization_ids)
    log_action(
        actor=actor,
        action=AuditAction.UPDATE,
        obj=profile,
        diff=make_diff(before, profile, ("employee_id",)),
    )
    return profile


def generate_password_hint() -> str:
    return get_random_string(16)


@transaction.atomic
def update_guardian_profile(
    *, user: User, phone: str, actor: User | None = None
) -> GuardianProfile:
    profile, _ = GuardianProfile.all_objects.get_or_create(user=user)
    before = snapshot(profile, ("phone",))
    profile.phone = phone.strip()
    profile.save(update_fields=["phone", "updated_at"])
    log_action(
        actor=actor,
        action=AuditAction.UPDATE,
        obj=profile,
        diff=make_diff(before, profile, ("phone",)),
    )
    return profile
