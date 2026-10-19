"""Hand-written student/guardian forms; group choices respect the boundary."""

from typing import Any

from django import forms

from accounts.models import GuardianProfile
from students.models import GuardianLink, Student


class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = (
            "group",
            "first_name",
            "last_name",
            "admission_no",
            "dob",
            "enrollment_date",
            "is_active",
        )
        help_texts = {"admission_no": "Unique within the institute."}

    def __init__(self, *args: Any, user: "object | None" = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if user is not None:
            from students.selectors import visible_groups_for_form

            self.fields["group"].queryset = visible_groups_for_form(user)

    def clean_admission_no(self) -> str:
        return self.cleaned_data["admission_no"].strip()


class GuardianLinkForm(forms.Form):
    guardian = forms.ModelChoiceField(
        label="Guardian",
        queryset=GuardianProfile.objects.all().select_related("user"),
        help_text="Only active guardian accounts can be linked.",
    )
    relationship = forms.ChoiceField(choices=GuardianLink.Relationship.choices)
    is_primary_contact = forms.BooleanField(
        required=False,
        label="Primary contact",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["guardian"].queryset = self.fields["guardian"].queryset.filter(
            deleted_at__isnull=True, user__is_active=True
        )
        self.fields["guardian"].label_from_instance = (
            lambda profile: f"{profile.user.get_full_name()} <{profile.user.email}>"
        )


class GuardianProfileForm(forms.ModelForm):
    class Meta:
        model = GuardianProfile
        fields = ("phone",)


class GuardianCreateForm(forms.Form):
    first_name = forms.CharField(max_length=80, label="First name")
    last_name = forms.CharField(max_length=80, label="Last name")
    email = forms.EmailField(
        label="Email", help_text="Used for login; a password-reset link can be sent later."
    )
    phone = forms.CharField(max_length=32, required=False, label="Phone")

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        from django.contrib.auth import get_user_model

        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean_phone(self) -> str:
        return self.cleaned_data["phone"].strip()

    def clean_first_name(self) -> str:
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self) -> str:
        return self.cleaned_data["last_name"].strip()


class GuardianUpdateForm(forms.Form):
    first_name = forms.CharField(max_length=80, label="First name")
    last_name = forms.CharField(max_length=80, label="Last name")
    email = forms.EmailField(label="Email", disabled=True)
    phone = forms.CharField(max_length=32, required=False, label="Phone")

    def __init__(self, *args: Any, user: "object | None" = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if user is not None:
            self.initial.setdefault("first_name", user.first_name)
            self.initial.setdefault("last_name", user.last_name)
            self.initial.setdefault("email", user.email)
            self.initial.setdefault(
                "phone", getattr(getattr(user, "guardian_profile", None), "phone", "")
            )

    def clean_phone(self) -> str:
        return self.cleaned_data["phone"].strip()

    def clean_first_name(self) -> str:
        return self.cleaned_data["first_name"].strip()

    def clean_last_name(self) -> str:
        return self.cleaned_data["last_name"].strip()
