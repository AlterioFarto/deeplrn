"""Role-aware navigation, built server-side (no template string matching)."""

from typing import Any

from django.urls import reverse

from common.roles import Role


def _item(label: str, url_name: str, icon: str, namespace: str) -> dict[str, str]:
    return {"label": label, "url": reverse(url_name), "icon": icon, "namespace": namespace}


def nav_items_for(user: Any) -> list[dict[str, str]]:
    if not user.is_authenticated:
        return []
    role = Role(user.role)
    if role == Role.ADMIN:
        return [
            _item("Dashboard", "dashboard:home", "home", "dashboard"),
            _item("Groups", "academics:group_list", "grid", "academics"),
            _item("Subjects", "academics:subject_list", "book", "academics"),
            _item("Time slots", "academics:timeslot_list", "clock", "academics"),
            _item("Timetable", "academics:schedule_list", "calendar", "academics"),
            _item("Exams", "academics:exam_list", "clipboard", "academics"),
            _item("Students", "students:student_list", "users", "students"),
            _item("Guardians", "students:guardian_list", "users", "students"),
            _item("Attendance", "attendance:attendance_list", "check", "attendance"),
            _item("Results", "results:result_list", "award", "results"),
            _item("Invoices", "billing:invoice_list", "wallet", "billing"),
            _item("Users", "accounts:user_list", "settings", "accounts"),
            _item("Reports", "dashboard:report_list", "file", "dashboard"),
        ]
    if role == Role.MENTOR:
        return [
            _item("Dashboard", "dashboard:home", "home", "dashboard"),
            _item("My groups", "academics:group_list", "grid", "academics"),
            _item("Timetable", "academics:schedule_list", "calendar", "academics"),
            _item("Exams", "academics:exam_list", "clipboard", "academics"),
            _item("Students", "students:student_list", "users", "students"),
            _item("Attendance", "attendance:attendance_list", "check", "attendance"),
            _item("Results", "results:result_list", "award", "results"),
        ]
    return [
        _item("Dashboard", "dashboard:home", "home", "dashboard"),
        _item("My students", "students:student_list", "users", "students"),
        _item("Attendance", "attendance:attendance_list", "check", "attendance"),
        _item("Results", "results:result_list", "award", "results"),
        _item("Invoices", "billing:invoice_list", "wallet", "billing"),
    ]


def navigation(request: Any) -> dict[str, Any]:
    return {"nav_items": nav_items_for(request.user)}
