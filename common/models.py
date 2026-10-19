"""Abstract base models, soft delete infrastructure and the audit log."""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    """QuerySet that treats ``delete()`` as a soft delete."""

    def delete(self):
        count = self.filter(deleted_at__isnull=True).update(deleted_at=timezone.now())
        return count, {self.model._meta.label: count}

    def hard_delete(self):
        return super().delete()

    def restore(self):
        return self.filter(deleted_at__isnull=False).update(deleted_at=None)

    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def deleted(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """Default manager: excludes soft-deleted rows."""

    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(TimeStampedModel):
    objects = SoftDeleteManager()
    all_objects = models.Manager()

    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        abstract = True
        base_manager_name = "all_objects"

    def delete(self, using=None, keep_parents=False):
        if self.deleted_at:
            return 0, {}
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at", "updated_at"])
        return 1, {self._meta.label: 1}

    def hard_delete(self, using=None, keep_parents=False):
        return super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at", "updated_at"])


class AuditLog(models.Model):
    """Append-only trail of security-relevant events (actor, object, diff)."""

    actor = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_entries",
    )
    actor_email = models.EmailField(blank=True)
    action = models.CharField(max_length=32)
    object_type = models.CharField(max_length=64, blank=True)
    object_id = models.CharField(max_length=64, blank=True)
    object_repr = models.CharField(max_length=255, blank=True)
    diff = models.JSONField(default=dict, blank=True)
    request_id = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["object_type", "object_id"], name="auditlog_object_idx")]
        verbose_name = "audit log entry"
        verbose_name_plural = "audit log entries"

    def __str__(self) -> str:
        return f"{self.action} {self.object_type}:{self.object_id}"
