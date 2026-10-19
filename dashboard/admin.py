from django.contrib import admin

from dashboard.models import ReportArtifact


@admin.register(ReportArtifact)
class ReportArtifactAdmin(admin.ModelAdmin):
    list_display = ("display_name", "stored_name", "size_bytes", "created_at", "task_id")
    search_fields = ("display_name", "stored_name")
