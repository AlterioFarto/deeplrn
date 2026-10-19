"""Small cache helpers used for dashboard aggregates and readiness checks."""

from django.core.cache import cache

READY_CHECK_KEY = "deeplrn:readyz"


def cache_roundtrip() -> bool:
    cache.set(READY_CHECK_KEY, "1", timeout=5)
    return cache.get(READY_CHECK_KEY) == "1"
