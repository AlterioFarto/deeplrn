"""Student records, guardian links and group enrolment history."""

from django.db import models
from django.db.models import Q, UniqueConstraint

from common.models import SoftDeleteModel, TimeStampedModel


class Student(SoftDeleteModel):
    first_name = models.CharField(max_length=80)
    last_name = models.CharField(max_length=80)
    admission_no = models.CharField(max_length=40)
    group = models.ForeignKey("academics.Group", on_delete=models.PROTECT, related_name="students")
    dob = models.DateField("date of birth", null=True, blank=True)
    enrollment_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["last_name", "first_name"]
        constraints = [
            UniqueConstraint(
                fields=["admission_no"],
                condition=Q(deleted_at__isnull=True),
                name="uniq_student_admission_no_alive",
            )
        ]
        indexes = [
            models.Index(fields=["group", "is_active"], name="student_group_active_idx"),
            models.Index(fields=["last_name", "first_name"], name="student_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name} ({self.admission_no})"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"


class GuardianLink(TimeStampedModel):
    """M2M through-model between Student and GuardianProfile."""

    class Relationship(models.TextChoices):
        MOTHER = "MOTHER", "Mother"
        FATHER = "FATHER", "Father"
        GUARDIAN = "GUARDIAN", "Guardian"
        SIBLING = "SIBLING", "Sibling"
        OTHER = "OTHER", "Other"

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="guardian_links")
    guardian = models.ForeignKey(
        "accounts.GuardianProfile", on_delete=models.PROTECT, related_name="student_links"
    )
    relationship = models.CharField(
        max_length=16, choices=Relationship.choices, default=Relationship.OTHER
    )
    is_primary_contact = models.BooleanField(default=False)

    class Meta:
        ordering = ["student__admission_no", "-is_primary_contact"]
        constraints = [
            UniqueConstraint(fields=["student", "guardian"], name="uniq_student_guardian_link"),
            UniqueConstraint(
                fields=["student"],
                condition=Q(is_primary_contact=True),
                name="uniq_student_primary_contact",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.guardian} ({self.get_relationship_display()}) of {self.student}"


class Enrollment(TimeStampedModel):
    """History of a student's membership in a group."""

    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name="enrollments")
    group = models.ForeignKey(
        "academics.Group", on_delete=models.PROTECT, related_name="enrollments"
    )
    academic_year = models.CharField(max_length=9)
    enrolled_on = models.DateField()
    left_on = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-enrolled_on"]
        constraints = [
            UniqueConstraint(
                fields=["student"],
                condition=Q(left_on__isnull=True),
                name="uniq_student_open_enrollment",
            ),
        ]
        indexes = [models.Index(fields=["student", "left_on"], name="enrollment_student_idx")]

    def __str__(self) -> str:
        return f"{self.student} in {self.group} ({self.academic_year})"
