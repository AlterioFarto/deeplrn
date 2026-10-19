"""Dashboard tests: cache lifecycle, role stats, report task."""

import pytest

from dashboard import selectors
from dashboard.caching import bump, key_for
from dashboard.models import ReportArtifact
from dashboard.tasks import generate_weekly_attendance_report

pytestmark = pytest.mark.django_db


def test_key_version_bump_invalidates():
    first = key_for(user_id=1)
    bump()
    assert key_for(user_id=1) != first


def test_admin_stats_keys(admin, student):
    stats = selectors.admin_stats(user=admin)
    assert {"student_count", "outstanding_total", "attendance_today", "trend", "at_risk"} <= set(
        stats.keys()
    )


def test_guardian_stats_keys(guardian_student):
    user = guardian_student.guardian_links.first().guardian.user
    stats = selectors.guardian_stats(user=user)
    assert {"students", "attendance_today", "trend"} <= set(stats.keys())


def test_weekly_report_task_creates_artifact(settings, tmp_path):
    settings.REPORTS_ROOT = str(tmp_path)
    generate_weekly_attendance_report()
    assert ReportArtifact.objects.exists()


def test_report_download_traversal_blocked(settings, tmp_path, admin_client):
    settings.REPORTS_ROOT = str(tmp_path)
    artifact = ReportArtifact.objects.create(
        display_name="evil.csv",
        stored_name="../secret.csv",
        size_bytes=1,
    )
    assert admin_client.get("/dashboard/reports/").status_code == 200
    response = admin_client.get(f"/dashboard/reports/{artifact.pk}/download/")
    assert response.status_code == 404
