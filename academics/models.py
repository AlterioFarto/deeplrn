"""Core academic structures: groups, subjects, time slots, timetable, exams."""

from django.conf import settings
from django.db import models
from django.db.models import F, Q

from common.models import TimeStampedModel
from common.roles import Role


class Group(TimeStampedModel):
    """A batch of students (first-class entity, the unit of scheduling)."""

    name = models.CharField(max_length=120, unique=True)
    academic_year = models.CharField(max_length=9)
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.CheckConstraint(condition=Q(capacity__gt=0), name="group_capacity_gt_0")
        ]
        indexes = [models.Index(fields=["is_active", "name"], name="group_active_name_idx")]

    def __str__(self) -> str:
        return f"{self.name} ({self.academic_year})"


class Subject(TimeStampedModel):
    """Reference data for anything exam- or timetable-related."""

    name = models.CharField(max_length=120, unique=True)
    code = models.CharField(max_length=20, unique=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} [{self.code}]"


class TimeSlot(TimeStampedModel):
    """A recurring period of the day; end_time must be after start_time."""

    name = models.CharField(max_length=80, unique=True)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        ordering = ["start_time"]
        constraints = [
            models.CheckConstraint(
                condition=Q(end_time__gt=F("start_time")), name="timeslot_end_after_start"
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.start_time:%H:%M}-{self.end_time:%H:%M})"


class Schedule(TimeStampedModel):
    """A recurring class on the weekly timetable."""

    class Day(models.IntegerChoices):
        MONDAY = 0, "Monday"
        TUESDAY = 1, "Tuesday"
        WEDNESDAY = 2, "Wednesday"
        THURSDAY = 3, "Thursday"
        FRIDAY = 4, "Friday"
        SATURDAY = 5, "Saturday"
        SUNDAY = 6, "Sunday"

    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="schedules")
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="schedules")
    mentor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="schedules",
        limit_choices_to={"role": Role.MENTOR},
    )
    timeslot = models.ForeignKey(TimeSlot, on_delete=models.PROTECT, related_name="schedules")
    day = models.PositiveSmallIntegerField(choices=Day.choices)

    class Meta:
        ordering = ["day", "timeslot__start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "day", "timeslot"], name="uniq_schedule_group_slot"
            ),
            models.UniqueConstraint(
                fields=["mentor", "day", "timeslot"], name="uniq_schedule_mentor_slot"
            ),
        ]
        indexes = [
            models.Index(fields=["group", "day"], name="schedule_group_day_idx"),
            models.Index(fields=["mentor", "day"], name="schedule_mentor_day_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.get_day_display()} {self.timeslot}: {self.subject} for {self.group}"


class Exam(TimeStampedModel):
    subject = models.ForeignKey(Subject, on_delete=models.PROTECT, related_name="exams")
    group = models.ForeignKey(Group, on_delete=models.PROTECT, related_name="exams")
    date = models.DateField()
    start_time = models.TimeField()
    duration_minutes = models.PositiveSmallIntegerField()
    max_marks = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="exams_created",
    )

    class Meta:
        ordering = ["-date", "start_time"]
        constraints = [
            models.CheckConstraint(condition=Q(max_marks__gt=0), name="exam_max_marks_gt_0"),
            models.CheckConstraint(
                condition=Q(duration_minutes__gt=0, duration_minutes__lte=600),
                name="exam_duration_1_600",
            ),
        ]
        indexes = [
            models.Index(fields=["group", "date"], name="exam_group_date_idx"),
            models.Index(fields=["date"], name="exam_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.subject} - {self.group} on {self.date}"
