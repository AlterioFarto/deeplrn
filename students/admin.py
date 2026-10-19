from django.contrib import admin

from students.models import Enrollment, GuardianLink, Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "admission_no",
        "first_name",
        "last_name",
        "group",
        "enrollment_date",
        "is_active",
        "deleted_at",
    )
    list_filter = ("group", "is_active")
    search_fields = ("admission_no", "first_name", "last_name")
    autocomplete_fields = ("group",)


@admin.register(GuardianLink)
class GuardianLinkAdmin(admin.ModelAdmin):
    list_display = ("student", "guardian", "relationship", "is_primary_contact")
    autocomplete_fields = ("student", "guardian")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("student", "group", "academic_year", "enrolled_on", "left_on")
    list_filter = ("academic_year", "group")
    autocomplete_fields = ("student", "group")
