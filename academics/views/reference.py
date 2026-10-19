"""Subject and time slot CRUD (admin-managed reference data)."""

from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from academics import services
from academics.forms import SubjectForm, TimeSlotForm
from academics.models import Subject, TimeSlot
from common.exceptions import ServiceError
from common.mixins import (
    ListWorkflowMixin,
    RoleRequiredMixin,
    ScopedAccessMixin,
    ServiceFormMixin,
)
from common.roles import Role

ADMIN_ONLY = frozenset({Role.ADMIN})


class SubjectListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Subject
    template_name = "common/object_list.html"
    allowed_roles = frozenset({Role.ADMIN, Role.MENTOR})
    search_fields = ["name", "code"]
    sort_fields = {"name": "name", "code": "code"}
    default_sort = "name"
    columns = [
        ("Subject", "name", "link"),
        ("Code", "code"),
        ("Exams", "exam_count"),
    ]
    export_name = "subjects"
    breadcrumbs = [("Subjects", None)]
    page_title = "Subjects"
    empty_message = "No subjects match the current filters."

    def get_queryset(self):
        from academics import selectors

        return selectors.subject_list_qs(q=self.request.GET.get("q", "").strip())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="academics:subject_update",
        )
        if self.current_user().role == Role.ADMIN:
            context.update(
                create_url=reverse("academics:subject_create"), create_label="Add subject"
            )
        return context


class SubjectCreateView(RoleRequiredMixin, ServiceFormMixin, CreateView):
    model = Subject
    form_class = SubjectForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.create_subject
    success_message = "Subject created."
    success_url = reverse_lazy("academics:subject_list")
    page_title = "Add subject"
    submit_label = "Create subject"
    breadcrumbs = [("Subjects", reverse_lazy("academics:subject_list")), ("Add subject", None)]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class SubjectUpdateView(RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, UpdateView):
    model = Subject
    form_class = SubjectForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.update_subject
    success_message = "Subject updated."
    success_url = reverse_lazy("academics:subject_list")
    page_title = "Edit subject"
    submit_label = "Save changes"
    breadcrumbs = [("Subjects", reverse_lazy("academics:subject_list")), ("Edit subject", None)]

    def service_kwargs(self, form: SubjectForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["subject"] = self.object
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class SubjectDeleteView(RoleRequiredMixin, ScopedAccessMixin, DeleteView):
    model = Subject
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    success_url = reverse_lazy("academics:subject_list")
    page_title = "Delete subject"

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_subject(subject=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("academics:subject_list")
        messages.success(self.request, "Subject deleted.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Subject “{self.object.name}” will be removed. Subjects referenced by "
                "exams or the timetable cannot be deleted."
            ),
            cancel_url=self.success_url,
        )
        return context


class TimeSlotListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = TimeSlot
    template_name = "common/object_list.html"
    allowed_roles = frozenset({Role.ADMIN, Role.MENTOR})
    search_fields = ["name"]
    default_sort = "start_time"
    columns = [
        ("Time slot", "name", "link"),
        ("Starts", "start_time", "time"),
        ("Ends", "end_time", "time"),
        ("Timetable entries", "schedule_count"),
    ]
    export_name = "timeslots"
    breadcrumbs = [("Time slots", None)]
    page_title = "Time slots"
    empty_message = "No time slots match the current filters."

    def get_queryset(self):
        from academics import selectors

        return selectors.timeslot_list_qs(q=self.request.GET.get("q", "").strip())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="academics:timeslot_update",
        )
        if self.current_user().role == Role.ADMIN:
            context.update(
                create_url=reverse("academics:timeslot_create"), create_label="Add time slot"
            )
        return context


class TimeSlotCreateView(RoleRequiredMixin, ServiceFormMixin, CreateView):
    model = TimeSlot
    form_class = TimeSlotForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.create_timeslot
    success_message = "Time slot created."
    success_url = reverse_lazy("academics:timeslot_list")
    page_title = "Add time slot"
    submit_label = "Create time slot"
    breadcrumbs = [("Time slots", reverse_lazy("academics:timeslot_list")), ("Add time slot", None)]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class TimeSlotUpdateView(RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, UpdateView):
    model = TimeSlot
    form_class = TimeSlotForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    service = services.update_timeslot
    success_message = "Time slot updated."
    success_url = reverse_lazy("academics:timeslot_list")
    page_title = "Edit time slot"
    submit_label = "Save changes"
    breadcrumbs = [
        ("Time slots", reverse_lazy("academics:timeslot_list")),
        ("Edit time slot", None),
    ]

    def service_kwargs(self, form: TimeSlotForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["timeslot"] = self.object
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class TimeSlotDeleteView(RoleRequiredMixin, ScopedAccessMixin, DeleteView):
    model = TimeSlot
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    success_url = reverse_lazy("academics:timeslot_list")
    page_title = "Delete time slot"

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_timeslot(timeslot=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("academics:timeslot_list")
        messages.success(self.request, "Time slot deleted.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Time slot “{self.object.name}” will be removed. Slots referenced by the "
                "timetable or attendance cannot be deleted."
            ),
            cancel_url=self.success_url,
        )
        return context
