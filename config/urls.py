"""Root URLconf for DEEPLRN.

Health and readiness probes stay unauthenticated and are also exempt from
URL redirects; everything else lives in per-app namespaces and requires a
session.
"""

from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.views.generic import RedirectView

from common import views as common_views


@csrf_exempt
@require_GET
def robots(request):
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


urlpatterns = [
    path("", RedirectView.as_view(url="/dashboard/", permanent=False), name="index"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("students/", include("students.urls")),
    path("academics/", include("academics.urls")),
    path("attendance/", include("attendance.urls")),
    path("results/", include("results.urls")),
    path("billing/", include("billing.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("health/", common_views.HealthView.as_view(), name="health"),
    path("ready/", common_views.ReadyView.as_view(), name="ready"),
    path("robots.txt", robots, name="robots"),
]


handler403 = "config.views.permission_denied"
handler404 = "config.views.not_found"
handler500 = "config.views.server_error"
