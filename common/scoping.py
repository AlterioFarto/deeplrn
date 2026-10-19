"""The single implementation of object-level authorization.

Every list, detail, mutation and export resolves its object set through an
``AuthorizationBoundary`` built from the current user's role:

* ADMIN    - unrestricted
* MENTOR   - objects of groups assigned via ``GroupAssignment``
* GUARDIAN - objects of students linked via ``GuardianLink``

Views use :func:`scoped_queryset` (unknown scope => empty queryset, fail
closed) and services additionally call :func:`assert_can_access` before
mutating, so authorization is enforced at both layers.
"""

from typing import TYPE_CHECKING, Any

from django.core.exceptions import FieldDoesNotExist, PermissionDenied
from django.db.models import Model, QuerySet

from common.roles import Role

if TYPE_CHECKING:
    from accounts.models import User as UserType


def get_boundary(user: Any) -> "AuthorizationBoundary":
    if not getattr(user, "is_authenticated", False):
        raise PermissionDenied("Authentication required.")
    return AuthorizationBoundary(user)


class AuthorizationBoundary:
    def __init__(self, user: "UserType") -> None:
        self.user = user
        self.role: Role = Role(user.role)

    def is_admin(self) -> bool:
        return self.role == Role.ADMIN

    def is_mentor(self) -> bool:
        return self.role == Role.MENTOR

    def is_guardian(self) -> bool:
        return self.role == Role.GUARDIAN

    # -- primitive scopes ---------------------------------------------------
    def group_ids(self) -> set[int] | None:
        """Primary keys of groups this user may see; ``None`` means all."""
        if self.is_admin():
            return None
        if self.is_mentor():
            MentorProfile = _model("accounts", "MentorProfile")
            profile = MentorProfile.all_objects.filter(user=self.user).first()
            if profile is None or profile.deleted_at:
                return set()
            return set(profile.groups.values_list("pk", flat=True))
        GuardianLink = _model("students", "GuardianLink")
        return set(
            GuardianLink.objects.filter(guardian__user=self.user).values_list(
                "student__group_id", flat=True
            )
        )

    def students_qs(self) -> QuerySet:
        Student = _model("students", "Student")
        if self.is_admin():
            return Student.objects.all()
        if self.is_mentor():
            return Student.objects.filter(group_id__in=self.group_ids())
        return Student.objects.filter(
            guardian_links__guardian__user=self.user,
            guardian_links__guardian__deleted_at__isnull=True,
        )

    # -- generic restrictions ------------------------------------------------
    def restrict_group(self, qs: QuerySet) -> QuerySet:
        ids = self.group_ids()
        return qs if ids is None else qs.filter(group_id__in=ids)

    def restrict_group_pk(self, qs: QuerySet) -> QuerySet:
        ids = self.group_ids()
        return qs if ids is None else qs.filter(pk__in=ids)

    def restrict_student(self, qs: QuerySet) -> QuerySet:
        if self.is_admin():
            return qs
        return qs.filter(student_id__in=self.students_qs().values("pk"))

    def restrict_invoice(self, qs: QuerySet) -> QuerySet:
        if self.is_admin():
            return qs
        return qs.filter(invoice__student_id__in=self.students_qs().values("pk"))


def _model(app_label: str, model_name: str) -> type[Model]:
    from django.apps import apps

    return apps.get_model(app_label, model_name)


def scoped_queryset(qs: QuerySet, user: Any) -> QuerySet:
    """Apply the user's boundary to a queryset; fail closed on unknown shapes."""
    boundary = get_boundary(user)
    if boundary.is_admin():
        return qs
    model = qs.model
    if model is _model("academics", "Group"):
        return boundary.restrict_group_pk(qs)
    if model is _model("students", "Student"):
        return qs.filter(pk__in=boundary.students_qs().values("pk"))
    for field, restrict in (
        ("group", boundary.restrict_group),
        ("student", boundary.restrict_student),
        ("invoice", boundary.restrict_invoice),
    ):
        try:
            model._meta.get_field(field)
        except FieldDoesNotExist:
            continue
        return restrict(qs)
    return qs.none()


def assert_can_access(user: Any, obj: Model) -> None:
    """Service-level guard: raise PermissionDenied unless the user may touch obj."""
    scoped = scoped_queryset(type(obj)._default_manager.filter(pk=obj.pk), user)
    if not scoped.exists():
        raise PermissionDenied("You do not have access to this object.")


def assert_can_manage_group(user: Any, group: Model) -> None:
    """Mutations inside a group require the group to be inside the boundary."""
    boundary = get_boundary(user)
    if boundary.is_admin():
        return
    if boundary.is_mentor() and group.pk in (boundary.group_ids() or set()):
        return
    raise PermissionDenied("You are not assigned to this group.")
