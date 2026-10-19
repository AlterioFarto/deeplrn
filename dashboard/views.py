"""Dashboard views: role-aware home and admin-only report downloads."""

from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.views.generic import TemplateView

from common.audit import log_action
from common.mixins import BreadcrumbMixin
from common.roles import AuditAction, Role
from dashboard import selectors
from dashboard.models import ReportArtifact


class HomeView(LoginRequiredMixin, BreadcrumbMixin, TemplateView):
    template_name = "dashboard/home.html"
    page_title = "Dashboard"
    breadcrumbs = [("Dashboard", None)]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            stats=selectors.cached_stats(self.current_user()),
            role=Role(self.current_user().role),
            # Dashboard cards need the nav template to know the module root.
            page_title=self.page_title,
            breadcrumbs=self.breadcrumbs,
        )
        # Charts read tuples/serialisable lists only.
        trend_view = list(context["stats"].get("trend", []))
        context["trend_json"] = [
            [
                row["date"].isoformat() if hasattr(row["date"], "isoformat") else str(row["date"]),
                row["percent"],
                row["marked"],
            ]
            for row in trend_view
        ]
        return context


class ReportsListView(BreadcrumbMixin, LoginRequiredMixin, TemplateView):
    template_name = "dashboard/reports.html"
    allowed_roles = frozenset({Role.ADMIN.value})
    page_title = "Reports"
    breadcrumbs = [("Dashboard", "/"), ("Reports", None)]

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        if self.current_user().role != Role.ADMIN.value:
            raise PermissionDenied("Your role cannot access this page.")
        artifacts = ReportArtifact.objects.all()[:50]
        # Deliberately list-only view; downloads carry their own audit entries.
        context["artifacts"] = [
            {
                "pk": artifact.pk,
                "display_name": artifact.display_name,
                "size_bytes": artifact.size_bytes,
                "created_at": artifact.created_at,
                "task_id": artifact.task_id,
            }
            for artifact in artifacts
        ]
        context["page_title"] = self.page_title
        context["breadcrumbs"] = self.breadcrumbs
        return context


class ReportDownloadView(BreadcrumbMixin, LoginRequiredMixin, TemplateView):
    allowed_roles = frozenset({Role.ADMIN.value})

    def get(self, request, pk: int, *args: Any, **kwargs: Any):
        if self.current_user().role != Role.ADMIN.value:
            raise PermissionDenied("Your role cannot access this page.")
        artifact = ReportArtifact.objects.filter(pk=pk).first()
        if artifact is None:
            raise Http404("Report not found.")
        root = Path(settings.REPORTS_ROOT).resolve()
        path = (root / Path(artifact.stored_name).name).resolve()
        if root not in path.parents or not path.is_file():
            raise Http404("Report file missing.")
        log_action(
            actor=self.current_user(),
            action=AuditAction.EXPORT,
            obj=artifact,
            diff={"download": artifact.stored_name},
        )
        return FileResponse(
            path.open("rb"),
            as_attachment=True,
            filename=artifact.display_name + ".csv",
        )
