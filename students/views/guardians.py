"""Guardian account management and student-guardian links."""

from typing import Any

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DeleteView, FormView, ListView, UpdateView, View

from accounts import services as account_services
from accounts.models import GuardianProfile
from common.exceptions import ServiceError
from common.mixins import BreadcrumbMixin, ListWorkflowMixin, RoleRequiredMixin
from common.roles import Role
from common.scoping import assert_can_access, get_boundary
from students import selectors as student_selectors
from students import services as student_services
from students.forms import GuardianCreateForm, GuardianLinkForm, GuardianUpdateForm
from students.models import GuardianLink, Student

ADMIN_ONLY = frozenset({Role.ADMIN})
STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})


class GuardianListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    template_name = "common/object_list.html"
    allowed_roles = STAFF_ROLES
    search_fields = ["user__first_name", "user__last_name", "user__email", "phone"]
    default_sort = "user__first_name"
    columns = [
        ("Name", "user__first_name", "link"),
        ("Email", "user__email"),
        ("Phone", "phone"),
        ("Linked students", "student_count"),
        ("Account", "user__is_active", "badge"),
    ]
    export_name = "guardians"
    page_title = "Guardians"
    empty_message = "No guardians match the current filters."
    breadcrumbs = [("Guardians", None)]

    def get_queryset(self):
        return student_selectors.guardian_list_qs(
            user=self.current_user(), q=self.request.GET.get("q", "").strip()
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="students:guardian_update",
        )
        if self.current_user().role == Role.ADMIN:
            context.update(
                create_url=reverse("students:guardian_create"), create_label="Add guardian"
            )
        return context


class GuardianCreateView(RoleRequiredMixin, BreadcrumbMixin, FormView):
    form_class = GuardianCreateForm
    template_name = "common/object_form.html"
    allowed_roles = ADMIN_ONLY
    page_title = "Add guardian"
    submit_label = "Create guardian"
    success_url = reverse_lazy("students:guardian_list")
    breadcrumbs = [("Guardians", reverse_lazy("students:guardian_list")), ("Add guardian", None)]

    def form_valid(self, form: GuardianCreateForm) -> Any:
        cleaned = form.cleaned_data
        user = account_services.create_user(
            email=cleaned["email"],
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
            role=Role.GUARDIAN,
            actor=self.current_user(),
        )
        account_services.update_guardian_profile(
            user=user, phone=cleaned["phone"], actor=self.current_user()
        )
        messages.success(
            self.request, "Guardian created. They can use “forgot password” to set a password."
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class GuardianUpdateView(RoleRequiredMixin, BreadcrumbMixin, UpdateView):
    model = GuardianProfile
    form_class = GuardianUpdateForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    page_title = "Edit guardian"
    submit_label = "Save changes"
    success_url = reverse_lazy("students:guardian_list")
    breadcrumbs = [("Guardians", reverse_lazy("students:guardian_list")), ("Edit guardian", None)]
    context_object_name = "guardian"

    def get_queryset(self):
        qs = GuardianProfile.objects.select_related("user")
        role = Role(self.current_user().role)
        if role == Role.ADMIN:
            return qs
        if role == Role.MENTOR:
            return qs.filter(
                student_links__student__group_id__in=get_boundary(self.current_user()).group_ids()
            ).distinct()
        return qs.none()

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.object.user
        return kwargs

    def form_valid(self, form: GuardianUpdateForm) -> Any:
        cleaned = form.cleaned_data
        account_services.update_user(
            user=self.object.user,
            actor=self.current_user(),
            first_name=cleaned["first_name"],
            last_name=cleaned["last_name"],
        )
        account_services.update_guardian_profile(
            user=self.object.user, phone=cleaned["phone"], actor=self.current_user()
        )
        messages.success(self.request, "Guardian updated.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class GuardianDeleteView(RoleRequiredMixin, BreadcrumbMixin, DeleteView):
    model = GuardianProfile
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    success_url = reverse_lazy("students:guardian_list")
    page_title = "Deactivate guardian"
    context_object_name = "guardian"
    breadcrumbs = [("Guardians", reverse_lazy("students:guardian_list")), ("Deactivate", None)]

    def form_valid(self, form: Any) -> Any:
        account_services.deactivate_user(user=self.object.user, actor=self.current_user())
        messages.success(
            self.request, "Guardian account deactivated. Linked students are unaffected."
        )
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Deactivate {self.object.user.get_full_name()}? They will no longer "
                "be able to log in and their student links are detached. "
                "Student records are kept."
            ),
            cancel_url=reverse("students:guardian_update", args=[self.object.pk]),
        )
        return context


def _can_access_student(user: Any, student: Student) -> bool:
    try:
        assert_can_access(user, student)
    except PermissionDenied:
        return False
    return True


class GuardianLinkView(RoleRequiredMixin, View):
    """POST-only: link a guardian to a student the actor can access."""

    allowed_roles = STAFF_ROLES
    http_method_names = ["post"]

    def post(self, request: Any, pk: int) -> Any:
        student = Student.objects.filter(pk=pk).first()
        if student is None or not _can_access_student(self.current_user(), student):
            raise Http404("Student not found.")
        form = GuardianLinkForm(request.POST)
        if form.is_valid():
            cleaned = form.cleaned_data
            try:
                student_services.link_guardian(
                    student=student,
                    guardian=cleaned["guardian"],
                    relationship=cleaned["relationship"],
                    is_primary_contact=cleaned["is_primary_contact"],
                    actor=self.current_user(),
                )
            except ServiceError as exc:
                messages.error(request, str(exc))
                return redirect("students:student_detail", pk=student.pk)
            messages.success(request, "Guardian linked.")
        else:
            for error_list in form.errors.values():
                messages.error(request, " ".join(error_list))
        return redirect("students:student_detail", pk=student.pk)


class GuardianUnlinkView(RoleRequiredMixin, View):
    allowed_roles = STAFF_ROLES
    http_method_names = ["post"]

    def post(self, request: Any, link_pk: int) -> Any:
        link = (
            GuardianLink.objects.select_related("student", "guardian__user")
            .filter(pk=link_pk)
            .first()
        )
        if link is None or not _can_access_student(self.current_user(), link.student):
            raise Http404("Link not found.")
        try:
            student_services.unlink_guardian(link=link, actor=self.current_user())
        except ServiceError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Guardian link removed.")
        return redirect("students:student_detail", pk=link.student_id)
