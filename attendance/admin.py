from django.contrib import admin

from attendance.models import Attendance, Policy


@admin.register(Policy)
class PolicyAdmin(admin.ModelAdmin):
    list_display = ("count_late_as_present", "count_excused_as_present")

    def has_add_permission(self, request) -> bool:
        # The singleton is created by Policy.load(); there is nothing to add.
        return not Policy.objects.exists()


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("date", "student", "timeslot", "status", "recorded_by", "notes")
    list_filter = ("status", "date", "student__group")
    search_fields = ("student__first_name", "student__last_name", "student__admission_no")
    autocomplete_fields = ("student", "timeslot", "recorded_by")
    date_hierarchy = "date"
