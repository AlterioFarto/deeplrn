"""Cross-app enums. Kept here so no app needs to import another app's models."""

from django.db.models import TextChoices


class Role(TextChoices):
    ADMIN = "ADMIN", "Admin"
    MENTOR = "MENTOR", "Mentor"
    GUARDIAN = "GUARDIAN", "Guardian"


STAFF_ROLES = frozenset({Role.ADMIN.value, Role.MENTOR.value})


class AuditAction(TextChoices):
    CREATE = "create", "Created"
    UPDATE = "update", "Updated"
    SOFT_DELETE = "soft_delete", "Soft deleted"
    RESTORE = "restore", "Restored"
    LOGIN = "login", "Logged in"
    LOGIN_FAILED = "login_failed", "Login failed"
    LOCKOUT = "lockout", "Account locked out"
    LOGOUT = "logout", "Logged out"
    ROLE_CHANGE = "role_change", "Role changed"
    BULK_ATTENDANCE = "bulk_attendance", "Bulk attendance recorded"
    BULK_RESULTS = "bulk_results", "Bulk results recorded"
    EXPORT = "export", "Data exported"
    REPORT = "report", "Report generated"
