"""Background jobs: weekly attendance digest report (Celery)."""

import csv
import uuid
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from common.audit import log_action
from common.roles import AuditAction


@shared_task(bind=True)
def generate_weekly_attendance_report(self) -> str:
    """Write a 7-day group attendance digest CSV into REPORTS_ROOT."""
    from django.db.models import Count, Q

    from academics.models import Group
    from attendance.models import Policy
    from dashboard.models import ReportArtifact

    end = timezone.localdate()
    start = end - timedelta(days=6)
    counted = Q(students__attendance__status="PRESENT")
    if Policy.load().count_late_as_present:
        counted |= Q(students__attendance__status="LATE")
    if Policy.load().count_excused_as_present:
        counted |= Q(students__attendance__status="EXCUSED")
    rows = (
        Group.objects.all()
        .annotate(
            total=Count(
                "students__attendance", filter=Q(students__attendance__date__range=(start, end))
            ),
            present=Count(
                "students__attendance",
                filter=counted & Q(students__attendance__date__range=(start, end)),
            ),
        )
        .order_by("name")
    )

    REPORTS_ROOT = Path(settings.REPORTS_ROOT)
    REPORTS_ROOT.mkdir(parents=True, exist_ok=True)
    stored_name = f"attendance-digest-{start:%Y%m%d}-{uuid.uuid4().hex[:8]}.csv"
    path = REPORTS_ROOT / stored_name
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["group", "academic_year", "records", "present", "percentage"])
        for row in rows:
            percentage = "" if not row.total else f"{row.present / row.total * 100:.1f}"
            writer.writerow([row.name, row.academic_year, row.total, row.present, percentage])

    artifact = ReportArtifact.objects.create(
        task_id=self.request.id or "eager",
        display_name=f"Weekly attendance digest ({start:%Y-%m-%d} to {end:%Y-%m-%d})",
        stored_name=stored_name,
        size_bytes=path.stat().st_size,
    )
    log_action(
        action=AuditAction.REPORT,
        actor=None,
        obj=artifact,
        diff={"report": stored_name, "rows": rows.count()},
    )
    return artifact.pk
