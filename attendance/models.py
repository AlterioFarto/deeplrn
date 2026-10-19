"""Daily attendance records and configurable attendance policy."""

from django.conf import settings
from django.db import models
from django.db.models import Q

from common.models import TimeStampedModel


class AttendanceStatus(models.TextChoices):
    PRESENT = "PRESENT", "Present"
    ABSENT = "ABSENT", "Absent"
    LATE = "LATE", "Late"
    EXCUSED = "EXCUSED", "Excused"


class Policy(TimeStampedModel):
    """Singleton configuring how attendance percentages are computed.

    Changing the policy changes how LATE/EXCUSED statuses count towards the
    percentage; select_numerator() is the single recompute path.
    """

    count_late_as_present = models.BooleanField(default=False)
    count_excused_as_present = models.BooleanField(default=True)

    class Meta:
        verbose_name = "attendance policy"
        verbose_name_plural = "attendance policy"

    def __str__(self) -> str:
        late = "counts" if self.count_late_as_present else "does not count"
        excused = "counts" if self.count_excused_as_present else "does not count"
        return f"LATE {late}, EXCUSED {excused} as present"

    @classmethod
    def load(cls) -> "Policy":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class Attendance(TimeStampedModel):
    Status = AttendanceStatus

    student = models.ForeignKey(
        "students.Student", on_delete=models.PROTECT, related_name="attendance"
    )
    date = models.DateField()
    timeslot = models.ForeignKey(
        "academics.TimeSlot",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="attendance_set",
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    recorded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_recorded",
    )
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-date", "timeslot__start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["student", "date", "timeslot"], name="uniq_attendance_slot"
            ),
            models.UniqueConstraint(
                fields=["student", "date"],
                condition=Q(timeslot__isnull=True),
                name="uniq_attendance_wholeday",
            ),
            models.CheckConstraint(
                condition=Q(status__in=AttendanceStatus.values), name="attendance_status_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["date"], name="attendance_date_idx"),
            models.Index(fields=["student", "date"], name="attendance_student_date_idx"),
        ]

    def __str__(self) -> str:
        slot = self.timeslot.name if self.timeslot else "Whole day"
        return f"{self.student} on {self.date} ({slot}): {self.status}"
