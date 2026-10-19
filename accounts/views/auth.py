"""Authentication and profile views."""

from typing import Any

from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import UpdateView

from accounts import security, services
from accounts.forms import LoginForm, ProfileForm
from accounts.models import User
from common.audit import log_action
from common.mixins import AuthenticatedUserMixin
from common.roles import AuditAction


class LoginView(auth_views.LoginView):
    template_name = "registration/login.html"
    form_class = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form: LoginForm) -> HttpResponse:
        email = form.cleaned_data["email"]
        ip = security.client_ip(self.request)
        locked = security.lockout_seconds_remaining(email, ip)
        if locked:
            form.add_error(
                None,
                f"Too many failed attempts. Try again in {max(locked // 60, 1)} minute(s).",
            )
            return self.form_invalid(form)
        user = authenticate(self.request, email=email, password=form.cleaned_data["password"])
        if user is None or not user.is_active:
            # Count wrong credentials as another failure (same as an invalid form).
            return self.form_invalid(form)
        login(self.request, user)
        security.clear_failures(email, ip)
        log_action(actor=user, action=AuditAction.LOGIN, obj=user)
        return HttpResponseRedirect(self.get_success_url())

    def form_invalid(self, form: LoginForm) -> HttpResponse:
        email = form.cleaned_data.get("email")
        if email:
            ip = security.client_ip(self.request)
            security.register_failure(email, ip)
            log_action(
                action=AuditAction.LOGIN_FAILED,
                diff={"email": email, "ip": ip},
            )
        return super().form_invalid(form)


class LogoutView(auth_views.LogoutView):
    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if self.current_user() is not None:
            log_action(actor=request.user, action=AuditAction.LOGOUT, obj=request.user)
        return super().post(request, *args, **kwargs)


class ProfileView(LoginRequiredMixin, AuthenticatedUserMixin, UpdateView):
    template_name = "accounts/profile.html"
    form_class = ProfileForm
    success_url = reverse_lazy("accounts:profile")

    def get_object(self, queryset: Any = None) -> User:
        return self.current_user()

    def form_valid(self, form: ProfileForm) -> HttpResponse:
        services.update_user(
            user=self.current_user(),
            actor=self.current_user(),
            first_name=form.cleaned_data["first_name"],
            last_name=form.cleaned_data["last_name"],
        )
        messages.success(self.request, "Profile updated.")
        return redirect(self.success_url)
