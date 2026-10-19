"""Custom user (email login, single role) and role profiles.

Role consistency is owned by ``accounts.services``: every role change and
profile creation happens inside one atomic transaction, and users are
deactivated (never hard-deleted) so references are reassigned or nulled
explicitly instead of cascading silently.
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import Q, UniqueConstraint

from common.models import SoftDeleteModel, TimeStampedModel
from common.roles import Role


class UserManager(BaseUserManager):
    """Manager for the email-login user model."""

    use_in_migrations = True

    def create_user(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> "User":
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: object
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.ADMIN)
        if extra_fields.get("is_staff") is not True or extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_staff=True and is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    username = None
    email = models.EmailField("email address", unique=True)
    role = models.CharField(
        max_length=16, choices=Role.choices, default=Role.GUARDIAN, db_index=True
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        ordering = ["email"]

    def __str__(self) -> str:
        return f"{self.get_full_name()} <{self.email}>" if self.get_full_name() else self.email

    @property
    def is_administrator(self) -> bool:
        return self.role == Role.ADMIN


class GuardianProfile(SoftDeleteModel):
    """Extra data for users with the GUARDIAN role."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.PROTECT, related_name="guardian_profile"
    )
    phone = models.CharField(max_length=32, blank=True)

    class Meta:
        ordering = ["user__email"]

    def __str__(self) -> str:
        return f"Guardian: {self.user}"


class MentorProfile(SoftDeleteModel):
    """Extra data and the group authorization boundary for MENTOR users."""

    user = models.OneToOneField(
        "accounts.User", on_delete=models.PROTECT, related_name="mentor_profile"
    )
    employee_id = models.CharField(max_length=32)
    specializations = models.ManyToManyField(
        "academics.Subject", blank=True, related_name="mentors"
    )
    groups = models.ManyToManyField(
        "academics.Group", through="GroupAssignment", related_name="assigned_mentors"
    )

    class Meta:
        ordering = ["user__email"]
        constraints = [
            UniqueConstraint(
                fields=["employee_id"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_mentor_employee_id_alive",
            )
        ]

    def __str__(self) -> str:
        return f"Mentor: {self.user} ({self.employee_id})"


class GroupAssignment(TimeStampedModel):
    """Assignment of a mentor to a group - the mentor authorization boundary."""

    mentor = models.ForeignKey(
        "accounts.MentorProfile", on_delete=models.PROTECT, related_name="group_assignments"
    )
    group = models.ForeignKey(
        "academics.Group", on_delete=models.PROTECT, related_name="mentor_assignments"
    )
    assigned_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="group_assignments_made",
    )

    class Meta:
        ordering = ["group__name", "mentor__user__email"]
        constraints = [
            UniqueConstraint(fields=["mentor", "group"], name="uniq_mentor_group_assignment")
        ]

    def __str__(self) -> str:
        return f"{self.mentor} -> {self.group}"
