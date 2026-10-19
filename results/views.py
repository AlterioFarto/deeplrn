"""Views for result lists, bulk entry per exam, and (admin) deletion."""

from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, ListView, View

from academics import selectors as academic_selectors
from academics.models import Exam
from common.exceptions import ServiceError
from common.mixins import ListWorkflowMixin, RoleRequiredMixin
from common.roles import Role
from results import services
from results.forms import build_results_entry_form, marks_from_form
from results.models import Result
from results.selectors import result_list_qs

STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})


class ResultListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Result
    template_name = "common/object_list.html"
    allowed_roles = frozenset({Role.ADMIN, Role.MENTOR, Role.GUARDIAN})
    search_fields = ["student__first_name", "student__last_name", "student__admission_no"]
    filter_params = {"exam": "exam_id"}
    sort_fields = {"exam": "exam__date", "marks": "marks"}
    default_sort = "-exam__date"
    columns = [
        ("Exam", "exam__subject__name", "link"),
        ("Date", "exam__date", "date"),
        ("Student", "student__full_name", "link"),
        ("Group", "exam__group__name"),
        ("Marks", "marks"),
        ("Out of", "exam__max_marks"),
        ("Grade", "grade", "badge"),
    ]
    export_name = "results"
    page_title = "Results"
    empty_message = "No results match the current filters."
    breadcrumbs = [("Results", None)]

    def get_queryset(self):
        return result_list_qs(
            user=self.current_user(),
            exam_id=self.request.GET.get("exam") or None,
            q=self.request.GET.get("q", "").strip() or None,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            filter_form_url=reverse("results:result_list"),
            exam_choices=academic_selectors.exam_list_qs(user=self.current_user()),
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(create_url=reverse("results:entry_list"), create_label="Enter results")
        return context


class ResultsEntryListView(RoleRequiredMixin, View):
    """Pick an exam to enter results for."""

    template_name = "results/entry_list.html"
    allowed_roles = STAFF_ROLES
    page_title = "Enter results"

    def get(self, request: Any) -> Any:
        from django.shortcuts import render

        exams = academic_selectors.exam_list_qs(user=self.current_user()).order_by(
            "-date", "start_time"
        )
        return render(request, self.template_name, {"exams": exams, "page_title": self.page_title})


class ResultsEntryView(RoleRequiredMixin, View):
    """Bulk marks entry for one exam; repeat submissions overwrite values."""

    template_name = "results/entry.html"
    allowed_roles = STAFF_ROLES

    def _exam(self, request: Any, exam_pk: int) -> Exam:
        try:
            return academic_selectors.exam_list_qs(user=self.current_user()).get(pk=exam_pk)
        except Exam.DoesNotExist as exc:
            raise Http404("Exam not found.") from exc

    def get(self, request: Any, exam_pk: int) -> Any:
        from django.shortcuts import render

        exam = self._exam(request, exam_pk)
        students = list(
            exam.group.students.filter(deleted_at__isnull=True, is_active=True).order_by(
                "last_name", "first_name"
            )
        )
        existing = {
            row["student_id"]: row["marks"]
            for row in Result.objects.filter(student__in=students, exam=exam).values(
                "student_id", "marks"
            )
        }
        context = {
            "page_title": f"Enter results - {exam}",
            "exam": exam,
            "entry_form": build_results_entry_form(students, existing, exam.max_marks),
            "entered_count": len(existing),
            "student_count": len(students),
            "cancel_url": reverse("academics:exam_detail", args=[exam.pk]),
            "breadcrumbs": [
                ("Results", reverse("results:result_list")),
                ("Enter results", None),
            ],
        }
        return render(request, self.template_name, context)

    def post(self, request: Any, exam_pk: int) -> Any:
        exam = self._exam(request, exam_pk)
        students = list(
            exam.group.students.filter(deleted_at__isnull=True, is_active=True).order_by(
                "last_name", "first_name"
            )
        )
        form = build_results_entry_form(students, {}, exam.max_marks)(data=request.POST)
        if not form.is_valid():
            messages.error(
                request, "Some marks are invalid. Values must be between 0 and the maximum."
            )
            return redirect("results:entry", exam_pk=exam.pk)
        try:
            saved = services.bulk_record_results(
                exam=exam, marks_by_student_id=marks_from_form(form), actor=self.current_user()
            )
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect("results:entry", exam_pk=exam.pk)
        except PermissionDenied:
            raise
        messages.success(request, f"Results saved for {saved} students.")
        return redirect("academics:exam_detail", pk=exam.pk)


class ResultDeleteView(RoleRequiredMixin, DeleteView):
    model = Result
    template_name = "common/object_confirm_delete.html"
    allowed_roles = STAFF_ROLES
    success_url = reverse_lazy("results:result_list")
    page_title = "Delete result"

    def get_queryset(self):
        from common.scoping import scoped_queryset

        return scoped_queryset(
            Result.objects.select_related("student", "exam"), self.current_user()
        )

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_result(result=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect(self.success_url)
        messages.success(self.request, "Result deleted.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Remove the result for {self.object.student} ({self.object.exam})? "
                "This cannot be undone."
            ),
            cancel_url=reverse("academics:exam_detail", args=[self.object.exam_id]),
        )
        return context
