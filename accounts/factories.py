import factory

from accounts.models import GroupAssignment, GuardianProfile, MentorProfile, User
from common.roles import Role


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("email",)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    role = Role.GUARDIAN

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "s3cure-test-passw0rd!")
        if create:
            self.save()

    @factory.post_generation
    def role_profile(self, create, extracted, **kwargs):
        if not create:
            return
        from accounts.services import _ensure_profile

        _ensure_profile(self, self.role.value)


class AdminUserFactory(UserFactory):
    role = Role.ADMIN
    is_staff = True


class MentorUserFactory(UserFactory):
    role = Role.MENTOR


class MentorProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MentorProfile

    user = factory.SubFactory(MentorUserFactory)
    employee_id = factory.Sequence(lambda n: f"MNT-{n:05d}")


class GuardianProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GuardianProfile

    user = factory.SubFactory("accounts.factories.GuardianUserFactory")
    phone = factory.Faker("phone_number")


class GuardianUserFactory(UserFactory):
    role = Role.GUARDIAN


class GroupAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GroupAssignment

    mentor = factory.SubFactory(MentorProfileFactory)
    group = factory.SubFactory("academics.factories.GroupFactory")
