"""Generated report artefact metadata (files live outside the web root)."""

from django.db import models

from common.models import TimeStampedModel


class ReportArtifact(TimeStampedModel):
    task_id = models.CharField(max_length=64)
    display_name = models.CharField(max_length=255)
    stored_name = models.CharField(max_length=128, unique=True)
    size_bytes = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.display_name
