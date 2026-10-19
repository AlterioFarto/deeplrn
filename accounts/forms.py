"""Hand-written forms for authentication and account management."""

from typing import Any

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.http import HttpRequest

from accounts.models import User
from common.roles import Role

UserModel = get_user_model()


class LoginForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(attrs={"autocomplete": "username", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}),
    )

    def __init__(self, request: HttpRequest | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.request = request


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Leave both password fields empty to send a password-reset link instead.",
    )
    password2 = forms.CharField(
        label="Confirm password",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "role")

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].strip().lower()
        if UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email

    def clean(self) -> dict:
        cleaned = super().clean()
        password1 = cleaned.get("password1") or ""
        password2 = cleaned.get("password2") or ""
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "The two passwords do not match.")
            else:
                user = UserModel(
                    email=cleaned.get("email", ""), first_name=cleaned.get("first_name", "")
                )
                validate_password(password1, user=user)
        return cleaned


class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "role", "is_active")


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["first_name"].widget.attrs.update({"autofocus": True})


ROLE_FILTER_CHOICES = [("", "All roles"), *Role.choices]
