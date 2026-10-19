"""Demo data seeding, dev-only and guarded by an environment flag.

Passwords are generated at runtime and printed once; nothing is hardcoded.
"""

import os
from datetime import time, timedelta
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.utils.crypto import get_random_string

from academics import services as academic_services
from accounts import services as account_services
from attendance import services as attendance_services
from attendance.models import Attendance
from billing import services as billing_services
from billing.models import Invoice
from common.roles import Role
from results import services as result_services
from students import services as student_services
from students.models import Student

_SUBJECTS = [
    ("Mathematics", "MATH"),
    ("Physics", "PHYS"),
    ("Computer Science", "CS"),
    ("English", "ENG"),
]
_GROUPS = [
    ("Alpha 2025", "2025/26", 15),
    ("Beta 2025", "2025/26", 15),
    ("Gamma 2026", "2026/27", 10),
]
_SLOTS = [
    ("1st period", time(8, 45), time(9, 45)),
    ("2nd period", time(9, 50), time(10, 50)),
    ("3rd period", time(10, 55), time(11, 55)),
]
_FIRST_NAMES = [
    "Maya",
    "Owen",
    "Leila",
    "Noah",
    "Iris",
    "Talha",
    "Sofia",
    "Ethan",
    "Zara",
    "Liam",
    "Nadia",
    "Omar",
]
_LAST_NAMES = ["Haddad", "Iyer", "Khan", "Moreau", "Nakamura", "Silva"]

CREDENTIALS: dict[str, str] = {}


def _credential(email: str) -> str:
    password = get_random_string(14)
    CREDENTIALS[email] = password
    return password


class Command(BaseCommand):
    help = "Seed demo data (dev runs only; requires DEEPLRN_SEED_DEMO=1 and DEBUG)."

    def handle(self, *args: Any, **options: Any) -> None:
        if os.environ.get("DEEPLRN_SEED_DEMO") != "1":
            raise CommandError("Refusing to seed: set DEEPLRN_SEED_DEMO=1 explicitly.")
        if not settings.DEBUG:
            raise CommandError("Refusing to seed: demo data only in DEBUG runs.")

        admin = account_services.create_user(
            email="admin@deeplrn.test",
            first_name="Ada",
            last_name="Admin",
            role=Role.ADMIN.value,
            password=_credential("admin@deeplrn.test"),
        )

        mentors = []
        for index in range(3):
            email = f"mentor{index + 1}@deeplrn.test"
            mentors.append(
                account_services.create_user(
                    email=email,
                    first_name=_FIRST_NAMES[index],
                    last_name=_LAST_NAMES[index],
                    role=Role.MENTOR.value,
                    password=_credential(email),
                )
            )

        guardian_profiles = []
        for index in range(4):
            email = f"guardian{index + 1}@deeplrn.test"
            user = account_services.create_user(
                email=email,
                first_name=_LAST_NAMES[index],
                last_name="Household",
                role=Role.GUARDIAN.value,
                password=_credential(email),
            )
            account_services.update_guardian_profile(
                user=user, phone=f"+1-555-010{index}", actor=admin
            )
            guardian_profiles.append(user.guardian_profile)

        subjects = [
            academic_services.create_subject(name=name, code=code, actor=admin)
            for name, code in _SUBJECTS
        ]
        slots = [
            academic_services.create_timeslot(
                name=name, start_time=start, end_time=end, actor=admin
            )
            for name, start, end in _SLOTS
        ]
        groups = [
            academic_services.create_group(
                name=name, academic_year=year, capacity=capacity, actor=admin
            )
            for name, year, capacity in _GROUPS
        ]

        for index, (group, mentor) in enumerate(zip(groups, mentors, strict=True)):
            account_services.assign_mentor_to_group(mentor=mentor, group=group, actor=admin)
            for day in (1, 3):
                academic_services.create_schedule(
                    group=group,
                    subject=subjects[index],
                    mentor=mentor,
                    timeslot=slots[index],
                    day=day,
                    actor=admin,
                )

        students: list[Student] = []
        for group_index, group in enumerate(groups):
            for number in range(4):
                email = _FIRST_NAMES[(group_index * 4 + number) % len(_FIRST_NAMES)]
                student_name_first = email
                student = student_services.create_student(
                    group=group,
                    first_name=student_name_first,
                    last_name=_LAST_NAMES[(group_index + number) % len(_LAST_NAMES)],
                    admission_no=f"S{2025}{group_index:02d}{number:03d}",
                    dob=timezone.localdate() - timedelta(days=(15 + group_index) * 365),
                    enrollment_date=timezone.localdate() - timedelta(days=30),
                    is_active=True,
                    actor=admin,
                )
                student_services.link_guardian(
                    student=student,
                    guardian=guardian_profiles[number % len(guardian_profiles)],
                    relationship="GUARDIAN",
                    is_primary_contact=number == 0,
                    actor=admin,
                )
                students.append(student)

        for group_index, group in enumerate(groups):
            group_students = list(
                Student.objects.filter(group=group, deleted_at__isnull=True, is_active=True)
            )
            for offset in range(14):
                on_date = timezone.localdate() - timedelta(days=offset)
                statuses = {}
                for local_index, student in enumerate(group_students):
                    roll = (group_index * 7 + offset * 3 + local_index) % 5
                    if roll == 0:
                        statuses[student.pk] = Attendance.Status.ABSENT
                    elif roll == 1:
                        statuses[student.pk] = Attendance.Status.LATE
                    else:
                        statuses[student.pk] = Attendance.Status.PRESENT
                attendance_services.bulk_record_attendance(
                    group=group,
                    on_date=on_date,
                    timeslot=None,
                    statuses=statuses,
                    recorded_by=mentors[group_index],
                    actor=admin,
                )

            exam = academic_services.create_exam(
                subject=subjects[group_index],
                group=group,
                date=timezone.localdate() - timedelta(days=3),
                start_time=slots[group_index].start_time,
                duration_minutes=60,
                max_marks=100,
                created_by=mentors[group_index],
                actor=admin,
            )
            marks = {
                student.pk: 55 + (group_index * 5 + local_index * 7) % 45
                for local_index, student in enumerate(group_students)
            }
            result_services.bulk_record_results(exam=exam, marks_by_student_id=marks, actor=admin)

        for student in Student.objects.filter(deleted_at__isnull=True, is_active=True):
            invoice = billing_services.create_invoice(
                student=student,
                period_start=timezone.localdate().replace(day=1),
                period_end=timezone.localdate() - timedelta(days=1),
                amount_due=500,
                due_date=timezone.localdate() - timedelta(days=1),
                status=Invoice.Status.ISSUED,
                actor=admin,
            )
            if invoice.pk % 2 == 0:
                billing_services.record_payment(
                    invoice=invoice,
                    amount=250,
                    paid_on=timezone.localdate(),
                    method="card",
                    receipt_no=f"RCPT-{student.pk:04d}",
                    recorded_by=admin,
                    actor=admin,
                )

        self.stdout.write(self.style.SUCCESS("Demo data seeded."))
        self.stdout.write("Generated credentials (dev only):")
        for email, password in CREDENTIALS.items():
            self.stdout.write(f"  {email} / {password}")
