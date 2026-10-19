"""Recompute derived grade letters from marks (single derivation path)."""

from typing import Any

from django.core.management.base import BaseCommand

from results.grades import grade_for
from results.models import Result


class Command(BaseCommand):
    help = "Recompute the denormalized grade on every result from marks and max marks."

    def handle(self, *args: Any, **options: Any) -> None:
        updated = 0
        checked = 0
        for result in Result.objects.select_related("exam").iterator(chunk_size=500):
            checked += 1
            grade = grade_for(result.marks, result.exam.max_marks)
            if grade != result.grade:
                result.grade = grade
                result.save(update_fields=["grade", "updated_at"])
                updated += 1
        self.stdout.write(f"Checked {checked} results; updated {updated} grades.")
