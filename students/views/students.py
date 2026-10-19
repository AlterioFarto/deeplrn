"""Student CRUD, detail, soft delete and restore."""

from typing import Any

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView, View

from academics.models import Group
from attendance.selectors import annotate_attendance, attendance_recent_qs
from billing.selectors import invoice_list_for_student, invoice_outstanding
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
from results.selectors import result_recent_qs
from students import services
from students.forms import GuardianLinkForm, StudentForm
from students.models import Student

STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})
ADMIN_ONLY = frozenset({Role.ADMIN})


class StudentListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Student
    template_name = "common/object_list.html"
    allowed_roles = STAFF_ROLES | {Role.GUARDIAN}
    search_fields = ["first_name", "last_name", "admission_no"]
    filter_params = {"group": "group_id", "status": "status"}
    sort_fields = {"name": "last_name", "admission": "admission_no"}
    default_sort = "last_name"
    columns = [
        ("Student", "full_name", "link"),
        ("Admission no.", "admission_no"),
        ("Group", "group__name"),
        ("Enrolled on", "enrollment_date", "date"),
        ("Guardians", "guardian_count"),
        ("Status", "is_active", "badge"),
    ]
    export_name = "students"
    breadcrumbs = [("Students", None)]
    page_title = "Students"
    empty_message = "No students match the current filters."

    def get_queryset(self):
        from students import selectors

        return selectors.student_list_qs(
            user=self.current_user(),
            q=self.request.GET.get("q", "").strip(),
            group_id=self.request.GET.get("group") or None,
            status=self.request.GET.get("status") or None,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="students:student_detail",
            filter_form_url=reverse("students:student_list"),
            group_choices=[
                ("", "All groups"),
                *[(g.pk, str(g)) for g in Group.objects.order_by("name")],
            ],
            status_choices=[("", "All"), ("active", "Active"), ("inactive", "Inactive")],
            hide_group_column=self.current_user().role == Role.GUARDIAN,
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(
                create_url=reverse("students:student_create"), create_label="Add student"
            )
        return context


class StudentCreateView(RoleRequiredMixin, ServiceFormMixin, BreadcrumbMixin, CreateView):
    model = Student
    form_class = StudentForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.create_student
    success_message = "Student enrolled."
    page_title = "Add student"
    submit_label = "Enroll student"
    breadcrumbs = [("Students", reverse_lazy("students:student_list")), ("Add student", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def get_success_url(self) -> str:
        return reverse("students:student_list")

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            submit_label=self.submit_label,
            cancel_url=reverse("students:student_list"),
        )
        return context


class StudentUpdateView(
    RoleRequiredMixin, ScopedAccessMixin, ServiceFormMixin, BreadcrumbMixin, UpdateView
):
    model = Student
    form_class = StudentForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    service = services.update_student
    success_message = "Student updated."
    page_title = "Edit student"
    submit_label = "Save changes"
    breadcrumbs = [("Students", reverse_lazy("students:student_list")), ("Edit student", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def service_kwargs(self, form: StudentForm) -> dict[str, Any]:
        kwargs = dict(form.cleaned_data)
        kwargs["student"] = self.object
        return kwargs

    def get_success_url(self) -> str:
        return reverse("students:student_detail", args=[self.object.pk])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=f"Edit {self.object.full_name}",
            submit_label=self.submit_label,
            cancel_url=reverse("students:student_detail", args=[self.object.pk]),
        )
        return context


class StudentDetailView(RoleRequiredMixin, DetailWorkflowMixin, DetailView):
    model = Student
    template_name = "students/student_detail.html"
    context_object_name = "student"
    allowed_roles = STAFF_ROLES | {Role.GUARDIAN}
    breadcrumbs = [("Students", reverse_lazy("students:student_list")), ("Detail", None)]

    def get_queryset(self):
        from students import selectors

        return selectors.student_detail_qs(user=self.current_user())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        student = self.object
        summary = annotate_attendance(Student.objects.filter(pk=student.pk)).first()
        context.update(
            page_title=student.full_name,
            linked_guardians=student.guardian_links.all(),
            guardian_link_form=GuardianLinkForm(),
            enrollments=student.enrollments.select_related("group").order_by("-enrolled_on"),
            attendance_pct=summary.attendance_pct if summary else None,
            recent_attendance=attendance_recent_qs(student),
            recent_results=result_recent_qs(student),
            invoices=invoice_list_for_student(student, user=self.current_user()),
            outstanding=invoice_outstanding(student),
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(
                edit_url=reverse("students:student_update", args=[student.pk]),
                delete_url=reverse("students:student_delete", args=[student.pk]),
                link_url=reverse("students:guardian_link", args=[student.pk]),
            )
        return context


class StudentDeleteView(RoleRequiredMixin, ScopedAccessMixin, BreadcrumbMixin, DeleteView):
    """Confirm page then soft delete through the service."""

    model = Student
    template_name = "common/object_confirm_delete.html"
    context_object_name = "student"
    allowed_roles = STAFF_ROLES
    page_title = "Remove student"
    success_url = reverse_lazy("students:student_list")
    breadcrumbs = [("Students", reverse_lazy("students:student_list")), ("Remove", None)]

    def form_valid(self, form: Any) -> Any:
        try:
            services.deactivate_student(student=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("students:student_detail", pk=self.object.pk)
        messages.success(
            self.request,
            f"{self.object.full_name} removed. Their history is kept and an admin can restore it.",
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Remove {self.object.full_name} ({self.object.admission_no})? "
                "Their history is kept and an admin can restore the record later."
            ),
            cancel_url=reverse("students:student_detail", args=[self.object.pk]),
        )
        return context


class StudentRestoreView(RoleRequiredMixin, View):
    """Admin-only restore of a soft-deleted student."""

    allowed_roles = ADMIN_ONLY
    http_method_names = ["post"]

    def post(self, request: Any, pk: int) -> Any:
        student = Student.all_objects.filter(pk=pk).first()
        if student is None or student.deleted_at is None:
            raise Http404("No restored record found.")
        services.restore_student(student=student, actor=self.current_user())
        messages.success(request, "Student restored.")
        return redirect("students:student_detail", pk=pk)
