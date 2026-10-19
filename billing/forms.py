"""Hand-written billing forms with explicit validation and help text."""

from typing import Any

from django import forms
from django.utils import timezone

from billing.models import Invoice, Payment


class InvoiceForm(forms.ModelForm):
    student = forms.ModelChoiceField(
        label="Student",
        queryset=None,
        help_text="Only students inside your authorization boundary are listed.",
    )

    class Meta:
        model = Invoice
        fields = ("period_start", "period_end", "amount_due", "due_date")
        help_texts = {
            "amount_due": "Total billed for the period; the outstanding balance is derived."
        }
        widgets = {
            "period_start": forms.DateInput(attrs={"type": "date"}),
            "period_end": forms.DateInput(attrs={"type": "date"}),
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "amount_due": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args: Any, user: "object | None" = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        from common.scoping import get_boundary
        from students.models import Student

        if user is not None:
            self.fields["student"].queryset = (
                get_boundary(user).students_qs().order_by("last_name", "first_name")
            )
        else:
            self.fields["student"].queryset = Student.objects.none()

    def clean(self) -> dict:
        cleaned = super().clean()
        start, end = cleaned.get("period_start"), cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "Period end must be on or after the start.")
        return cleaned


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ("amount", "paid_on", "method", "receipt_no", "notes")
        help_texts = {"receipt_no": "Unique receipt number; cannot exceed the remaining balance."}
        widgets = {
            "paid_on": forms.DateInput(attrs={"type": "date"}),
            "amount": forms.NumberInput(attrs={"step": "0.01", "min": "0.01"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields["paid_on"].initial = timezone.localdate()

    def clean_amount(self) -> forms.DecimalField:
        return self.cleaned_data["amount"]
