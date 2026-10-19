from django.contrib import admin

from academics.models import Exam, Group, Schedule, Subject, TimeSlot


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "academic_year", "capacity", "student_count", "is_active")
    list_filter = ("is_active", "academic_year")
    search_fields = ("name",)

    def student_count(self, obj) -> int:
        return obj.students.filter(deleted_at__isnull=True).count()

    student_count.short_description = "Students"


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "code")
    search_fields = ("name", "code")


@admin.register(TimeSlot)
class TimeSlotAdmin(admin.ModelAdmin):
    list_display = ("name", "start_time", "end_time")
    search_fields = ("name",)


@admin.register(Schedule)
class ScheduleAdmin(admin.ModelAdmin):
    list_display = ("day", "timeslot", "subject", "group", "mentor")
    list_filter = ("day", "group")
    search_fields = ("group__name", "subject__name", "mentor__email")


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = ("subject", "group", "date", "start_time", "duration_minutes", "max_marks")
    list_filter = ("group", "subject", "date")
    search_fields = ("subject__name", "group__name")
