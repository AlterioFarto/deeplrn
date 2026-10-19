"""Bulk result entry form for an exam, one field per student in the group."""

from decimal import Decimal
from typing import Any

from django import forms


def build_results_entry_form(
    students: Any, existing: dict[int, Decimal], max_marks: int
) -> type[forms.Form]:
    fields: dict[str, forms.Field] = {}
    for student in students:
        initial = existing.get(student.pk, None)
        fields[f"marks_{student.pk}"] = forms.DecimalField(
            label=f"{student.full_name} ({student.admission_no})",
            required=False,
            initial=initial,
            min_value=0,
            max_value=max_marks,
            max_digits=6,
            decimal_places=2,
            widget=forms.NumberInput(
                attrs={"inputmode": "decimal", "placeholder": f"0-{max_marks}"}
            ),
        )
    return type("ResultsEntryForm", (forms.Form,), fields)


def marks_from_form(form: Any) -> dict[int, Decimal]:
    """Cleaned-data map {student_id: Decimal}; blank entries are skipped."""
    marks: dict[int, Decimal] = {}
    for field_name, value in form.cleaned_data.items():
        if not field_name.startswith("marks_") or value in (None, ""):
            continue
        marks[int(field_name.removeprefix("marks_"))] = Decimal(str(value))
    return marks
