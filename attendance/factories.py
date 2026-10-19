import factory
from django.utils import timezone

from attendance.models import Attendance, Policy


class PolicyFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Policy
        django_get_or_create = ("pk",)

    count_late_as_present = False
    count_excused_as_present = True


class AttendanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Attendance

    student = factory.SubFactory("students.factories.StudentFactory")
    date = factory.LazyFunction(timezone.localdate)
    timeslot = None
    status = Attendance.Status.PRESENT
    recorded_by = factory.SubFactory("accounts.factories.AdminUserFactory")
    notes = ""
