import factory
from django.utils import timezone

from students.models import Enrollment, GuardianLink, Student


class StudentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Student
        django_get_or_create = ("admission_no",)

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    admission_no = factory.Sequence(lambda n: f"ADM-{n:05d}")
    group = factory.SubFactory("academics.factories.GroupFactory")
    enrollment_date = factory.LazyFunction(timezone.localdate)
    is_active = True


class EnrollmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Enrollment

    student = factory.SubFactory(StudentFactory)
    group = factory.SelfAttribute(".student.group")
    academic_year = factory.SelfAttribute(".student.group.academic_year")
    enrolled_on = factory.LazyAttribute(lambda o: o.student.enrollment_date)


class GuardianLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GuardianLink

    student = factory.SubFactory(StudentFactory)
    guardian = factory.SubFactory("accounts.factories.GuardianProfileFactory")
    relationship = GuardianLink.Relationship.MOTHER
    is_primary_contact = True
