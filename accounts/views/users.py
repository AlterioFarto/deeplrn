"""Admin-only user management views. All writes go through services."""

from typing import Any

from django.contrib import messages
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, ListView, UpdateView

from accounts import services
from accounts.forms import UserCreateForm, UserUpdateForm
from accounts.models import User
from common.mixins import BreadcrumbMixin, ListWorkflowMixin, RoleRequiredMixin
from common.roles import Role


class UserListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = User
    template_name = "common/object_list.html"
    allowed_roles = frozenset({Role.ADMIN})
    search_fields = ["email", "first_name", "last_name"]
    filter_params = {"role": "role"}
    columns = [
        ("Email", "email"),
        ("Name", "first_name"),
        ("Role", "role", "badge"),
        ("Active", "is_active", "bool"),
        ("Last login", "last_login", "datetime"),
    ]
    export_name = "users"

    def get_queryset(self):
        from accounts.selectors import user_list_qs

        return user_list_qs(
            q=self.request.GET.get("q", "").strip(),
            role=self.request.GET.get("role", "").strip(),
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title="Users",
            create_url=reverse("accounts:user_create"),
            create_label="Add user",
            empty_message="No users match the current filters.",
        )
        return context


class UserCreateView(RoleRequiredMixin, BreadcrumbMixin, CreateView):
    model = User
    form_class = UserCreateForm
    template_name = "common/object_form.html"
    success_url = reverse_lazy("accounts:user_list")
    allowed_roles = frozenset({Role.ADMIN})
    breadcrumbs = [("Users", "/accounts/users/"), ("Add user", None)]

    def form_valid(self, form: UserCreateForm) -> HttpResponse:
        cleaned = form.cleaned_data
        services.create_user(
            email=cleaned["email"],
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            role=cleaned["role"],
            password=cleaned.get("password1") or None,
            actor=self.current_user(),
        )
        messages.success(self.request, "User created.")
        return redirect(self.success_url)


class UserUpdateView(RoleRequiredMixin, BreadcrumbMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = "common/object_form.html"
    success_url = reverse_lazy("accounts:user_list")
    allowed_roles = frozenset({Role.ADMIN})
    breadcrumbs = [("Users", "/accounts/users/"), ("Edit user", None)]

    def form_valid(self, form: UserUpdateForm) -> HttpResponse:
        cleaned = form.cleaned_data
        target = self.get_object()
        if target == self.current_user():
            self.request.session.modified = False
            cleaned_role = None
            cleaned_active = None
            messages.warning(self.request, "You cannot change your own role or active state.")
        else:
            cleaned_role = cleaned["role"]
            cleaned_active = cleaned["is_active"]
        services.update_user(
            user=target,
            actor=self.current_user(),
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            role=cleaned_role,
            is_active=cleaned_active,
        )
        messages.success(self.request, "User updated.")
        return redirect(self.success_url)
