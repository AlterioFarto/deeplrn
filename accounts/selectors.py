"""Read paths for account management."""

from django.db.models import Count, QuerySet

from accounts.models import GuardianProfile, MentorProfile, User
from common.roles import Role


def user_list_qs(*, q: str | None = None, role: str | None = None) -> QuerySet[User]:
    qs = User.objects.select_related("guardian_profile", "mentor_profile").all()
    if q:
        qs = (
            qs.filter(email__icontains=q)
            | qs.filter(first_name__icontains=q)
            | qs.filter(last_name__icontains=q)
        )
    if role:
        qs = qs.filter(role=role)
    return qs


def mentor_list_qs(*, q: str | None = None) -> QuerySet[MentorProfile]:
    qs = (
        MentorProfile.objects.select_related("user")
        .annotate(
            group_count=Count("groups", distinct=True),
            specialization_count=Count("specializations", distinct=True),
        )
        .all()
    )
    if q:
        qs = (
            qs.filter(user__email__icontains=q)
            | qs.filter(user__first_name__icontains=q)
            | qs.filter(user__last_name__icontains=q)
            | qs.filter(employee_id__icontains=q)
        )
    return qs


def guardian_list_qs(*, user: User, q: str | None = None) -> QuerySet[GuardianProfile]:
    """Guardians scoped to the requester's boundary."""
    qs = GuardianProfile.objects.select_related("user").annotate(
        student_count=Count("student_links", distinct=True)
    )
    role = Role(user.role)
    if role == Role.MENTOR:
        from common.scoping import get_boundary

        qs = qs.filter(
            student_links__student__group_id__in=get_boundary(user).group_ids()
        ).distinct()
    elif role == Role.GUARDIAN:
        qs = qs.filter(user=user)
    if q:
        qs = (
            qs.filter(user__email__icontains=q)
            | qs.filter(user__first_name__icontains=q)
            | qs.filter(user__last_name__icontains=q)
        )
    return qs
