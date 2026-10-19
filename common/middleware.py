"""Project middleware: request correlation and Permissions-Policy header."""

import re
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponseBase

from common.context import new_request_id, reset_request_id, set_request_id

_INBOUND_REQUEST_ID = re.compile(r"^[0-9a-zA-Z-]{8,64}$")


class RequestIDMiddleware:
    """Attach a per-request id (honouring a trusted upstream X-Request-ID)."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        inbound = request.headers.get("X-Request-ID", "")
        request_id = inbound if _INBOUND_REQUEST_ID.fullmatch(inbound) else new_request_id()
        request.request_id = request_id
        token = set_request_id(request_id)
        try:
            response = self.get_response(request)
        finally:
            reset_request_id(token)
        response.headers["X-Request-ID"] = request_id
        return response


class PermissionsPolicyMiddleware:
    """Emit a Permissions-Policy header from settings.PERMISSIONS_POLICY."""

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponseBase:
        response = self.get_response(request)
        policy = getattr(settings, "PERMISSIONS_POLICY", {})
        if policy:
            value = ", ".join(
                f"{feature}=({','.join(allowlist)})" for feature, allowlist in policy.items()
            )
            response.headers["Permissions-Policy"] = value
        return response
