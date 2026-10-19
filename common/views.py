"""Health and readiness probes (safe to expose unauthenticated)."""

from django.db import connection
from django.http import JsonResponse
from django.views import View

from common.cache_utils import cache_roundtrip
from common.context import get_request_id


class HealthView(View):
    """Liveness: the process is up and can serve requests."""

    def get(self, request):
        return JsonResponse({"status": "ok", "request_id": get_request_id()})


class ReadyView(View):
    """Readiness: database and cache respond; 503 otherwise."""

    def get(self, request):
        checks = {"database": "ok", "cache": "ok"}
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception:
            checks["database"] = "error"
        if not cache_roundtrip():
            checks["cache"] = "error"
        healthy = all(value == "ok" for value in checks.values())
        return JsonResponse(
            {
                "status": "ok" if healthy else "degraded",
                "checks": checks,
                "request_id": get_request_id(),
            },
            status=200 if healthy else 503,
        )
