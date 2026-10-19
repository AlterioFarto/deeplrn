import factory
from django.utils import timezone

from academics.models import Exam, Group, Schedule, Subject, TimeSlot


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Group
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Group {n}")
    academic_year = "2025-2026"
    capacity = 30
    is_active = True


class SubjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Subject
        django_get_or_create = ("code",)

    name = factory.Sequence(lambda n: f"Subject {n}")
    code = factory.Sequence(lambda n: f"SUB{n:03d}")


class TimeSlotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TimeSlot
        django_get_or_create = ("name",)

    name = factory.Sequence(lambda n: f"Slot {n}")
    start_time = "09:00"
    end_time = "10:00"


class ExamFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exam

    subject = factory.SubFactory(SubjectFactory)
    group = factory.SubFactory(GroupFactory)
    date = factory.LazyFunction(timezone.localdate)
    start_time = "09:00"
    duration_minutes = 60
    max_marks = 100


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Schedule

    group = factory.SubFactory(GroupFactory)
    subject = factory.SubFactory(SubjectFactory)
    mentor = factory.SubFactory("accounts.factories.MentorUserFactory")
    timeslot = factory.SubFactory(TimeSlotFactory)
    day = Schedule.Day.MONDAY
