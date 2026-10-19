"""Cache-backed login throttling and account lockout (backend-agnostic)."""

import hashlib
import time
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def _key(email: str, ip: str) -> str:
    digest = hashlib.sha256(f"{email.lower()}|{ip}".encode()).hexdigest()
    return f"deeplrn:login-attempts:{digest}"


def lockout_seconds_remaining(email: str, ip: str) -> int:
    data: dict[str, Any] = cache.get(_key(email, ip)) or {}
    remaining = int((data.get("locked_until") or 0) - time.time())
    return max(0, remaining)


def register_failure(email: str, ip: str) -> int:
    """Record a failed attempt; lock the identity when the limit is reached."""
    key = _key(email, ip)
    data = cache.get(key) or {"attempts": 0, "locked_until": None}
    data["attempts"] = int(data.get("attempts", 0)) + 1
    if data["attempts"] >= settings.LOGIN_MAX_ATTEMPTS:
        data["locked_until"] = time.time() + settings.LOGIN_LOCKOUT_SECONDS
        data["attempts"] = 0
    cache.set(key, data, timeout=max(settings.LOGIN_LOCKOUT_SECONDS * 2, 60))
    return int(data["attempts"])


def clear_failures(email: str, ip: str) -> None:
    cache.delete(_key(email, ip))
