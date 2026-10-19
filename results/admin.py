from django.contrib import admin

from results.models import Result


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("student", "exam", "marks", "grade")
    list_filter = ("grade", "exam__group")
    search_fields = (
        "student__first_name",
        "student__last_name",
        "student__admission_no",
        "exam__subject__name",
    )
    autocomplete_fields = ("student", "exam")
