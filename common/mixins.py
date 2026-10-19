"""Reusable class-based view mixins: scoping, roles, search, tables, CSV export."""

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone
from django.views.generic.list import MultipleObjectMixin

from common.audit import log_action
from common.csv import streaming_csv_response
from common.pagination import CappedPaginator, get_page_size
from common.roles import AuditAction
from common.scoping import scoped_queryset

if TYPE_CHECKING:
    from accounts.models import User


class AuthenticatedUserMixin:
    """Provide ``current_user()`` for views that require a signed-in user."""

    def current_user(self) -> "User":
        """The request user, guaranteed authenticated by LoginRequiredMixin."""
        user = self.request.user
        if user.is_anonymous:
            raise PermissionDenied("Please sign in.")
        return user  # type: ignore[no-any-return]


class BreadcrumbMixin(AuthenticatedUserMixin):
    """``breadcrumbs`` is a list of (label, url|None) tuples set by subclasses."""

    breadcrumbs: "list[tuple[str, Any]]" = []

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["breadcrumbs"] = self.breadcrumbs
        return context


class DetailWorkflowMixin(BreadcrumbMixin):
    """Breadcrumbs and page chrome for detail pages."""


class RoleRequiredMixin(AuthenticatedUserMixin, LoginRequiredMixin):
    """Allow only the given roles; every authenticated role when None."""

    allowed_roles: frozenset[str] | None = None

    def dispatch(self, request: HttpRequest, *args: Any, **kwargs: Any) -> Any:
        if (
            request.user.is_authenticated
            and self.allowed_roles is not None
            and request.user.role not in self.allowed_roles
        ):
            raise PermissionDenied("Your role cannot access this page.")
        return super().dispatch(request, *args, **kwargs)


class ScopedAccessMixin(LoginRequiredMixin):
    """Restrict get_queryset() to the current user's authorization boundary."""

    def get_queryset(self) -> QuerySet:
        return scoped_queryset(super().get_queryset(), self.request.user)


class PaginationMixin(MultipleObjectMixin):
    """Page size from the request, capped by settings."""

    def get_paginate_by(self, queryset: QuerySet) -> int:
        return get_page_size(self.request)

    def get_paginator(self, queryset: QuerySet, per_page: int, **kwargs: Any) -> CappedPaginator:
        return CappedPaginator(queryset, per_page, **kwargs)


class SearchListMixin:
    """GET-parameter search, whitelisted filters and sorting for list views."""

    search_fields: list[str] = []
    filter_params: dict[str, str] = {}
    sort_fields: dict[str, str] = {}
    default_sort: str = "-pk"

    def get_queryset(self) -> QuerySet:
        qs = super().get_queryset()
        q = (self.request.GET.get("q") or "").strip()
        if q and self.search_fields:
            conditions = Q()
            for field in self.search_fields:
                conditions |= Q(**{f"{field}__icontains": q})
            qs = qs.filter(conditions)
        for param, lookup in self.filter_params.items():
            value = (self.request.GET.get(param) or "").strip()
            if value:
                qs = qs.filter(**{lookup: value})
        sort = (self.request.GET.get("sort") or "").strip()
        if sort and sort.lstrip("-") in {s.lstrip("-") for s in self.sort_fields.values()}:
            qs = qs.order_by(sort)
        elif self.default_sort:
            qs = qs.order_by(self.default_sort)
        return qs

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["active_filters"] = self._active_filters()
        return context

    def _active_filters(self) -> dict[str, str]:
        params: dict[str, str] = {}
        for key in ("q", *self.filter_params.keys(), "sort"):
            value = self.request.GET.get(key, "")
            if value:
                params[key] = value
        return params


def normalize_columns(columns: list[tuple]) -> list[dict[str, Any]]:
    return [
        {"header": column[0], "path": column[1], "format": column[2] if len(column) > 2 else "text"}
        for column in columns
    ]


class ColumnTableMixin:
    """Shared table/CSV column metadata so lists and exports never diverge."""

    columns: list[tuple] = []

    def get_columns(self) -> list[dict[str, Any]]:
        return normalize_columns(self.columns)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context["columns"] = self.get_columns()
        return context

    @staticmethod
    def render_row(obj: Any, columns: list[dict[str, Any]]) -> list[Any]:
        values = []
        for column in columns:
            current: Any = obj
            for part in column["path"].split("__"):
                if current is None or part.startswith("_"):
                    current = None
                    break
                current = getattr(current, part, None)
            if callable(current):
                current = current()
            values.append(current)
        return values


class CsvExportMixin:
    """Serve the current (scoped, filtered) queryset as a streaming CSV export."""

    export_name: str = "export"

    def get(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if request.GET.get("export") == "csv":
            return self.export_csv(request)
        return super().get(request, *args, **kwargs)

    def export_csv(self, request: HttpRequest) -> HttpResponse:
        columns = self.get_columns()
        rows = (
            self.render_row(obj, columns) for obj in self.get_queryset().iterator(chunk_size=500)
        )
        log_action(
            actor=request.user,
            action=AuditAction.EXPORT,
            diff={"export": self.export_name, "filters": self._active_filters()},
        )
        return streaming_csv_response(
            filename=f"{self.export_name}-{timezone.localdate():%Y%m%d}.csv",
            headers=[column["header"] for column in columns],
            rows=rows,
        )


class ListWorkflowMixin(
    SearchListMixin, ColumnTableMixin, CsvExportMixin, PaginationMixin, BreadcrumbMixin
):
    """Everything a DEEPLRN list view needs in one mixin."""


class ServiceFormMixin:
    """Route form submissions through a domain service instead of saving the form.

    Subclasses set ``service`` (a callable taking keyword arguments) and
    ``success_message``. ``service_kwargs`` maps cleaned data to service kwargs.
    """

    service: Callable[..., Any] = None  # type: ignore[assignment]
    success_message: str = "Saved."

    def service_kwargs(self, form: Any) -> dict[str, Any]:
        return dict(form.cleaned_data)

    def form_valid(self, form: Any) -> Any:
        from django.contrib import messages
        from django.shortcuts import redirect

        from common.exceptions import ServiceError

        try:
            self.service(**self.service_kwargs(form), actor=self.request.user)
        except ServiceError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, self.success_message)
        return redirect(self.get_success_url())
