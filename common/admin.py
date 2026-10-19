from django.contrib import admin

from common.models import AuditLog

admin.site.register(
    AuditLog,
    list_display=("created_at", "actor_email", "action", "object_type", "object_id"),
    list_filter=("action",),
    search_fields=("actor_email", "object_repr"),
    readonly_fields=(
        "created_at",
        "actor",
        "actor_email",
        "action",
        "object_type",
        "object_id",
        "object_repr",
        "diff",
        "request_id",
    ),
    ordering=("-created_at",),
)
