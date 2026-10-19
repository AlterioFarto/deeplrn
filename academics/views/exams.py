"""Exam CRUD and detail views."""

from typing import Any

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from academics import selectors, services
from academics.forms import ExamForm
from academics.models import Exam
from common.exceptions import ServiceError
from common.mixins import (
    DetailWorkflowMixin,
    ListWorkflowMixin,
    RoleRequiredMixin,
    ScopedAccessMixin,
    ServiceFormMixin,
)
from common.roles import Role

STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})


class ExamListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Exam
    template_name = "common/object_list.html"
    allowed_roles = STAFF_ROLES
    filter_params = {"group": "group_id"}
    sort_fields = {"date": "date", "subject": "subject__name"}
    default_sort = "-date"
    columns = [
        ("Date", "date", "date"),
        ("Subject", "subject__name", "link"),
        ("Group", "group__name"),
        ("Starts", "start_time", "time"),
        ("Max marks", "max_marks"),
        ("Results entered", "result_count"),
    ]
    export_name = "exams"
    breadcrumbs = [("Exams", None)]
    page_title = "Exams"
    empty_message = "No exams match the current filters."

    def get_queryset(self):
        return selectors.exam_list_qs(
            user=self.current_user(), group_id=self.request.GET.get("group") or None
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="academics:exam_detail",
            filter_form_url=reverse("academics:exam_list"),
            group_choices=[
                (g.pk, str(g)) for g in selectors.visible_groups_for_form(self.current_user())
            ],
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(create_url=reverse("academics:exam_create"), create_label="Add exam")
        return context


class ExamCreateView(RoleRequiredMixin, ServiceFormMixin, CreateView):
    model = Exam
    form_class = ExamForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.create_exam
    success_message = "Exam created."
    success_url = reverse_lazy("academics:exam_list")
    page_title = "Add exam"
    submit_label = "Create exam"
    breadcrumbs = [("Exams", reverse_lazy("academics:exam_list")), ("Add exam", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def service_kwargs(self, form: ExamForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["created_by"] = self.current_user()
        return kwargs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class ExamUpdateView(RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, UpdateView):
    model = Exam
    form_class = ExamForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.update_exam
    success_message = "Exam updated."
    page_title = "Edit exam"
    submit_label = "Save changes"
    breadcrumbs = [("Exams", reverse_lazy("academics:exam_list")), ("Edit exam", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def service_kwargs(self, form: ExamForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["exam"] = self.object
        return kwargs

    def get_success_url(self) -> str:
        return reverse("academics:exam_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            submit_label=self.submit_label,
            cancel_url=reverse("academics:exam_detail", args=[self.object.pk]),
        )
        return context


class ExamDeleteView(RoleRequiredMixin, ScopedAccessMixin, DeleteView):
    model = Exam
    template_name = "common/object_confirm_delete.html"
    allowed_roles = STAFF_ROLES
    success_url = reverse_lazy("academics:exam_list")
    page_title = "Delete exam"

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_exam(exam=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("academics:exam_detail", pk=self.object.pk)
        messages.success(self.request, "Exam deleted.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Exam “{self.object}” will be removed. "
                "Exams with recorded results cannot be deleted."
            ),
            cancel_url=reverse("academics:exam_detail", args=[self.object.pk]),
        )
        return context


class ExamDetailView(RoleRequiredMixin, DetailWorkflowMixin, DetailView):
    model = Exam
    template_name = "academics/exam_detail.html"
    context_object_name = "exam"
    allowed_roles = STAFF_ROLES
    breadcrumbs = [("Exams", reverse_lazy("academics:exam_list")), ("Detail", None)]

    def get_queryset(self):
        return selectors.exam_list_qs(user=self.current_user())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        exam = self.object
        from results.models import Result

        results = (
            Result.objects.filter(exam=exam)
            .select_related("student")
            .order_by("student__admission_no")
        )
        context.update(
            page_title=str(exam),
            results=results,
            entered_count=results.count(),
            student_count=exam.group.students.filter(deleted_at__isnull=True).count(),
            can_edit=self.current_user().role in STAFF_ROLES,
            entry_url=reverse("results:entry", args=[exam.pk]),
            edit_url=reverse("academics:exam_update", args=[exam.pk]),
            delete_url=reverse("academics:exam_delete", args=[exam.pk]),
        )
        return context
