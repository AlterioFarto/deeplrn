"""Weekly timetable views."""

from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from academics import selectors, services
from academics.forms import ScheduleForm
from academics.models import Schedule
from common.exceptions import ServiceError
from common.mixins import (
    ListWorkflowMixin,
    RoleRequiredMixin,
    ScopedAccessMixin,
    ServiceFormMixin,
)
from common.roles import Role

STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})
ADMIN_ONLY = frozenset({Role.ADMIN})


class ScheduleListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Schedule
    template_name = "common/object_list.html"
    allowed_roles = STAFF_ROLES
    filter_params = {"group": "group_id", "day": "day"}
    sort_fields = {"day": "day", "slot": "timeslot__start_time"}
    default_sort = "day"
    columns = [
        ("Day", "get_day_display"),
        ("Time", "timeslot__name"),
        ("Starts", "timeslot__start_time", "time"),
        ("Ends", "timeslot__end_time", "time"),
        ("Subject", "subject__name"),
        ("Group", "group__name", "link"),
        ("Mentor", "mentor__first_name"),
    ]
    export_name = "timetable"
    breadcrumbs = [("Timetable", None)]
    page_title = "Timetable"
    empty_message = "No timetable entries match the current filters."

    def get_queryset(self):
        group_id = self.request.GET.get("group") or None
        day = self.request.GET.get("day") or None
        return selectors.schedule_list_qs(user=self.current_user(), group_id=group_id, day=day)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="academics:schedule_update",
            filter_form_url=reverse("academics:schedule_list"),
            group_choices=[
                (g.pk, str(g)) for g in selectors.visible_groups_for_form(self.current_user())
            ],
            day_choices=Schedule.Day.choices,
        )
        if self.current_user().role == Role.ADMIN:
            context.update(
                create_url=reverse("academics:schedule_create"), create_label="Add entry"
            )
        return context


class ScheduleCreateView(RoleRequiredMixin, ServiceFormMixin, CreateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.create_schedule
    success_message = "Timetable entry created."
    success_url = reverse_lazy("academics:schedule_list")
    page_title = "Add timetable entry"
    submit_label = "Create entry"
    breadcrumbs = [("Timetable", reverse_lazy("academics:schedule_list")), ("Add entry", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class ScheduleUpdateView(RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, UpdateView):
    model = Schedule
    form_class = ScheduleForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.update_schedule
    success_message = "Timetable entry updated."
    success_url = reverse_lazy("academics:schedule_list")
    page_title = "Edit timetable entry"
    submit_label = "Save changes"
    breadcrumbs = [("Timetable", reverse_lazy("academics:schedule_list")), ("Edit entry", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def service_kwargs(self, form: ScheduleForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["schedule"] = self.object
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class ScheduleDeleteView(RoleRequiredMixin, ScopedAccessMixin, DeleteView):
    model = Schedule
    template_name = "common/object_confirm_delete.html"
    allowed_roles = STAFF_ROLES
    success_url = reverse_lazy("academics:schedule_list")
    page_title = "Delete timetable entry"

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_schedule(schedule=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("academics:schedule_list")
        messages.success(self.request, "Timetable entry deleted.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=f"Remove “{self.object}” from the timetable? This cannot be undone.",
            cancel_url=self.success_url,
        )
        return context
