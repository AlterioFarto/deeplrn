"""Dashboard caching: versioned keys invalidated on domain writes."""

from django.core.cache import cache

_VERSION_KEY = "deeplrn:dashboard:version"


def version() -> int:
    return int(cache.get(_VERSION_KEY, 1))


def bump() -> None:
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        cache.set(_VERSION_KEY, 2)


def key_for(user_id: int) -> str:
    return f"deeplrn:dashboard:v{version()}:user:{user_id}"
