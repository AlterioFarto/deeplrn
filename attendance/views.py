"""Attendance list and bulk recording views."""

from datetime import date, timedelta
from typing import Any

from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.generic import ListView, View

from academics.models import Group, TimeSlot
from attendance import selectors, services
from attendance.forms import AttendanceSelectionForm, build_entry_form
from attendance.models import Attendance
from common.exceptions import ServiceError
from common.mixins import ListWorkflowMixin, RoleRequiredMixin
from common.roles import Role
from students.models import Student

ALL_ROLES = frozenset({Role.ADMIN, Role.MENTOR, Role.GUARDIAN})
STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})


def _today() -> date:
    return timezone.localdate()


class AttendanceListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Attendance
    template_name = "common/object_list.html"
    allowed_roles = ALL_ROLES
    search_fields = ["student__first_name", "student__last_name", "student__admission_no"]
    filter_params = {"group": "student__group_id", "status": "status"}
    sort_fields = {"date": "date", "student": "student__last_name"}
    default_sort = "-date"
    columns = [
        ("Date", "date", "date"),
        ("Student", "student__full_name", "link"),
        ("Group", "student__group__name"),
        ("Period", "timeslot__name"),
        ("Status", "status", "badge"),
        ("Recorded by", "recorded_by__first_name"),
        ("Notes", "notes"),
    ]
    export_name = "attendance"
    page_title = "Attendance"
    empty_message = "No attendance records match the current filters."
    breadcrumbs = [("Attendance", None)]

    def get_queryset(self):
        on_date = parse_iso(self.request.GET.get("date"))
        start, end = parse_range(self.request.GET.get("range"))
        if start is None and on_date is not None:
            start = on_date
        return selectors.attendance_list_qs(
            user=self.current_user(),
            q=self.request.GET.get("q", "").strip() or None,
            group_id=_int_or_none(self.request.GET.get("group")),
            status=self.request.GET.get("status") or None,
            start=start,
            end=end if end or start else None,
            on_date=on_date if start is None else None,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="students:student_detail",
            filter_form_url=reverse("attendance:attendance_list"),
            group_choices=[(g.pk, str(g)) for g in Group.objects.order_by("name")],
            status_choices=Attendance.Status.choices,
            range_choices=[
                ("", "All dates"),
                ("today", "Today"),
                ("7", "Last 7 days"),
                ("30", "Last 30 days"),
            ],
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(
                create_url=reverse("attendance:record"), create_label="Record attendance"
            )
        return context


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def parse_iso(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def parse_range(value: str | None) -> tuple[date | None, date | None]:
    if value == "today":
        today = _today()
        return today, today
    if value in {"7", "30"}:
        end = _today()
        return end - timedelta(days=int(value)), end
    return None, None


class AttendanceRecordView(RoleRequiredMixin, View):
    """Two-stage bulk recorder: select group/date/period, then mark students."""

    template_name = "attendance/record.html"
    allowed_roles = STAFF_ROLES

    def get(self, request: HttpRequest) -> HttpResponse:
        selection = AttendanceSelectionForm(
            request.GET if request.GET.get("group") else None, user=self.current_user()
        )
        context: dict[str, Any] = {
            "page_title": "Record attendance",
            "selection_form": selection,
            "breadcrumbs": [
                ("Attendance", reverse("attendance:attendance_list")),
                ("Record", None),
            ],
            "cancel_url": reverse("attendance:attendance_list"),
        }
        if request.GET.get("group") and selection.is_valid():
            group, on_date, timeslot = self._selection(selection)
            students = list(
                Student.objects.filter(
                    group=group, deleted_at__isnull=True, is_active=True
                ).order_by("last_name", "first_name")
            )
            existing = {
                row["student_id"]: row["status"]
                for row in Attendance.objects.filter(
                    student__in=students, date=on_date, timeslot=timeslot
                ).values("student_id", "status")
            }
            context.update(
                students=students,
                group=group,
                on_date=on_date,
                timeslot=timeslot,
                whole_day=timeslot is None,
                entry_form=build_entry_form(students, existing, whole_day=timeslot is None),
                already_recorded=bool(existing),
            )
        return render(request, self.template_name, context)

    def post(self, request: HttpRequest) -> HttpResponse:
        selection = AttendanceSelectionForm(request.POST, user=self.current_user())
        if not selection.is_valid():
            messages.error(request, "Select a valid group and date.")
            return redirect("attendance:record")
        group, on_date, timeslot = self._selection(selection)
        students = list(
            Student.objects.filter(group=group, deleted_at__isnull=True, is_active=True).order_by(
                "last_name", "first_name"
            )
        )
        existing = {
            row["student_id"]: row["status"]
            for row in Attendance.objects.filter(
                student__in=students, date=on_date, timeslot=timeslot
            ).values("student_id", "status")
        }
        entry_form = build_entry_form(students, existing, whole_day=timeslot is None)(
            data=request.POST
        )
        if not entry_form.is_valid():
            messages.error(request, "Choose a status for every student.")
            return redirect(f"{reverse('attendance:record')}?{request.POST.urlencode()}")
        statuses = {
            int(field_name.removeprefix("status_")): value
            for field_name, value in entry_form.cleaned_data.items()
        }
        try:
            saved = services.bulk_record_attendance(
                group=group,
                on_date=on_date,
                timeslot=timeslot,
                statuses=statuses,
                recorded_by=self.current_user(),
                actor=self.current_user(),
            )
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect(f"{reverse('attendance:record')}?{request.POST.urlencode()}")
        except PermissionDenied:
            raise
        messages.success(request, f"Attendance saved for {saved} students.")
        return redirect(
            f"{reverse('attendance:attendance_list')}?date={on_date.isoformat()}&group={group.pk}"
        )

    @staticmethod
    def _selection(form: forms.Form) -> tuple[Group, date, TimeSlot | None]:
        cleaned = form.cleaned_data
        return cleaned["group"], cleaned["date"], cleaned.get("timeslot")
