"""HTML error handlers so 4xx/5xx pages keep the site chrome."""

from django.shortcuts import render


def permission_denied(request, exception=None):
    return render(request, "common/error.html", {"code": 403, "title": "Not permitted"}, status=403)


def not_found(request, exception=None):
    return render(
        request, "common/error.html", {"code": 404, "title": "Page not found"}, status=404
    )


def server_error(request):
    return render(
        request, "common/error.html", {"code": 500, "title": "Something went wrong"}, status=500
    )
