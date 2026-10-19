"""Hand-written forms for academics; querysets are always boundary-scoped."""

import re
from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

from academics import selectors
from academics.models import Exam, Group, Schedule, Subject, TimeSlot
from accounts.models import User
from common.roles import Role

UserModel = get_user_model()

academic_year_validator = RegexValidator(
    regex=re.compile(r"^\d{4}-\d{4}$"),
    message="Use the format 2025-2026.",
)


class GroupForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("name", "academic_year", "capacity", "is_active")
        help_texts = {
            "academic_year": "Academic year as YYYY-YYYY.",
            "capacity": "Maximum number of active students.",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["academic_year"].validators.append(academic_year_validator)
        self.fields["capacity"].min_value = 1

    def clean_name(self) -> str:
        return self.cleaned_data["name"].strip()


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ("name", "code")

    def clean_code(self) -> str:
        return self.cleaned_data["code"].strip().upper()


class TimeSlotForm(forms.ModelForm):
    class Meta:
        model = TimeSlot
        fields = ("name", "start_time", "end_time")

    def clean(self) -> dict:
        cleaned = super().clean()
        start, end = cleaned.get("start_time"), cleaned.get("end_time")
        if start and end and end <= start:
            self.add_error("end_time", "End time must be after start time.")
        return cleaned


class ScheduleForm(forms.ModelForm):
    class Meta:
        model = Schedule
        fields = ("group", "subject", "mentor", "timeslot", "day")

    def __init__(self, *args: Any, user: "User | None" = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["group"].queryset = selectors.visible_groups_for_form(user)
        self.fields["mentor"].queryset = (
            UserModel.objects.filter(
                role=Role.MENTOR, is_active=True, mentor_profile__deleted_at__isnull=True
            )
            .select_related("mentor_profile")
            .order_by("first_name", "last_name")
        )
        self.fields["mentor"].label_from_instance = (
            lambda mentor: f"{mentor.get_full_name()} ({mentor.mentor_profile.employee_id})"
        )

    def clean(self) -> dict:
        cleaned = super().clean()
        group, mentor = cleaned.get("group"), cleaned.get("mentor")
        if group and mentor and not selectors.mentor_can_teach_group(mentor=mentor, group=group):
            self.add_error(
                "mentor",
                "This mentor is not assigned to the selected group. "
                "Assign them to the group first.",
            )
        return cleaned


class ExamForm(forms.ModelForm):
    class Meta:
        model = Exam
        fields = ("subject", "group", "date", "start_time", "duration_minutes", "max_marks")
        help_texts = {"duration_minutes": "Exam duration in minutes (1-600)."}

    def __init__(self, *args: Any, user: "User | None" = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["group"].queryset = selectors.visible_groups_for_form(user)
        self.fields["duration_minutes"].min_value = 1
        self.fields["max_marks"].min_value = 1
