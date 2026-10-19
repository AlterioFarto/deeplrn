"""Shared pagination: capped page size, URL-preserving."""

from typing import Any

from django.conf import settings
from django.core.paginator import Paginator
from django.http import HttpRequest

PAGE_SIZE_PARAM = "page_size"


def get_page_size(request: HttpRequest) -> int:
    default = getattr(settings, "PAGE_SIZE", 25)
    maximum = getattr(settings, "MAX_PAGE_SIZE", 100)
    try:
        requested = int(request.GET.get(PAGE_SIZE_PARAM, default))
    except (TypeError, ValueError):
        return default
    return max(1, min(requested, maximum))


class CappedPaginator(Paginator):
    """Paginator that never exceeds the configured maximum page size."""

    def __init__(self, object_list: Any, per_page: int, **kwargs: Any) -> None:
        maximum = getattr(settings, "MAX_PAGE_SIZE", 100)
        super().__init__(object_list, min(per_page or maximum, maximum), **kwargs)
