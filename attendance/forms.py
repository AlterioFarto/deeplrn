"""Forms for recording attendance (selection stage + dynamic entry stage)."""

from typing import Any

from django import forms
from django.utils import timezone

from academics.models import Group, TimeSlot
from attendance.models import Attendance
from common.scoping import get_boundary


class AttendanceSelectionForm(forms.Form):
    group = forms.ModelChoiceField(label="Group", queryset=Group.objects.none())
    date = forms.DateField(
        label="Date", initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"})
    )
    timeslot = forms.ModelChoiceField(
        label="Period",
        queryset=TimeSlot.objects.order_by("start_time"),
        required=False,
        empty_label="Whole day",
        help_text="Leave empty to record attendance for the whole day.",
    )

    def __init__(self, *args: Any, user: Any = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["group"].queryset = get_boundary(user).restrict_group_pk(
            Group.objects.filter(is_active=True).order_by("name")
        )


def build_entry_form(
    students: Any, existing: dict[int, str], *, whole_day: bool
) -> type[forms.Form]:
    """Build a per-student radio form; each row carries the current status."""
    fields: dict[str, forms.Field] = {}
    for student in students:
        fields[f"status_{student.pk}"] = forms.ChoiceField(
            choices=Attendance.Status.choices,
            initial=existing.get(student.pk, Attendance.Status.PRESENT),
            widget=forms.RadioSelect,
            label=f"{student.full_name} ({student.admission_no})",
            required=True,
        )
    return type("AttendanceEntryForm", (forms.Form,), {**fields, "whole_day": whole_day})
