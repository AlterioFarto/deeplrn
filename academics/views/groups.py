"""Group CRUD and detail views."""

from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from academics import services
from academics.forms import GroupForm
from academics.models import Group
from common.exceptions import ServiceError
from common.mixins import (
    BreadcrumbMixin,
    DetailWorkflowMixin,
    ListWorkflowMixin,
    RoleRequiredMixin,
    ScopedAccessMixin,
    ServiceFormMixin,
)
from common.roles import Role

ADMIN_ONLY = frozenset({Role.ADMIN})
STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})


class GroupListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Group
    template_name = "common/object_list.html"
    allowed_roles = STAFF_ROLES
    search_fields = ["name", "academic_year"]
    sort_fields = {"name": "name", "capacity": "capacity"}
    default_sort = "name"
    columns = [
        ("Group", "name", "link"),
        ("Academic year", "academic_year"),
        ("Students", "student_count"),
        ("Capacity", "capacity"),
        ("Mentors", "mentor_count"),
        ("Status", "is_active", "badge"),
    ]
    export_name = "groups"
    breadcrumbs = [("Groups", None)]

    def get_queryset(self):
        from academics import selectors

        return selectors.group_list_qs(
            user=self.current_user(), q=self.request.GET.get("q", "").strip()
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title="Groups",
            empty_message="No groups match the current filters.",
        )
        if self.current_user().role == Role.ADMIN:
            context["create_url"] = reverse("academics:group_create")
            context["create_label"] = "Add group"
        return context


class GroupCreateView(RoleRequiredMixin, ServiceFormMixin, BreadcrumbMixin, CreateView):
    model = Group
    form_class = GroupForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.create_group
    success_message = "Group created."
    breadcrumbs = [("Groups", reverse_lazy("academics:group_list")), ("Add group", None)]
    success_url = reverse_lazy("academics:group_list")
    page_title = "Add group"
    submit_label = "Create group"
    cancel_url = reverse_lazy("academics:group_list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.cancel_url
        )
        return context


class GroupUpdateView(
    RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, BreadcrumbMixin, UpdateView
):
    model = Group
    form_class = GroupForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.update_group
    success_message = "Group updated."
    page_title = "Edit group"
    submit_label = "Save changes"
    cancel_url = reverse_lazy("academics:group_list")

    def service_kwargs(self, form: GroupForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["group"] = self.object
        return kwargs

    def get_success_url(self) -> str:
        return reverse("academics:group_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            submit_label=self.submit_label,
            cancel_url=reverse("academics:group_detail", args=[self.object.pk]),
        )
        return context


class GroupDeleteView(RoleRequiredMixin, ScopedAccessMixin, BreadcrumbMixin, DeleteView):
    model = Group
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    context_object_name = "object"
    page_title = "Delete group"

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_group(group=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("academics:group_detail", pk=self.object.pk)
        messages.success(self.request, "Group deleted.")
        return redirect("academics:group_list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Group “{self.object.name}” and its references will be removed. "
                "Groups with students or timetable entries cannot be deleted."
            ),
            cancel_url=reverse("academics:group_detail", args=[self.object.pk]),
        )
        return context


class GroupDetailView(RoleRequiredMixin, DetailWorkflowMixin, DetailView):
    model = Group
    template_name = "academics/group_detail.html"
    context_object_name = "group"
    allowed_roles = STAFF_ROLES
    breadcrumbs = [("Groups", reverse_lazy("academics:group_list")), ("Detail", None)]

    def get_queryset(self):
        from academics import selectors

        return selectors.group_detail_qs(user=self.current_user())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        group = self.object
        context.update(
            page_title=str(group),
            students=group.students.filter(deleted_at__isnull=True).order_by(
                "last_name", "first_name"
            ),
            schedules=group.schedules.select_related("subject", "timeslot", "mentor").order_by(
                "day", "timeslot__start_time"
            ),
            mentors=group.assigned_mentors.select_related("user"),
        )
        if self.current_user().role == Role.ADMIN:
            context["actions"] = {
                "edit_url": reverse("academics:group_update", args=[group.pk]),
                "delete_url": reverse("academics:group_delete", args=[group.pk]),
            }
        return context
