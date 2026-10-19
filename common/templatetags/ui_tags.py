"""Design-system template tags: icons, badges, currency, stat cards, form fields."""

import decimal
from typing import Any

from django import forms as django_forms
from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.formats import number_format
from django.utils.html import format_html

register = template.Library()

_TONE_BY_VALUE = {
    "active": "ok",
    "present": "ok",
    "paid": "ok",
    "true": "ok",
    "inactive": "muted",
    "draft": "muted",
    "void": "muted",
    "absent": "danger",
    "overdue": "danger",
    "late": "warn",
    "issued": "info",
    "excused": "info",
    "partial": "warn",
}

# Feather-style 24x24 stroke icons (https://feathericons.com, MIT license).
_ICONS: dict[str, str] = {
    "home": '<path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/>',
    "users": '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
    "book": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>',
    "clipboard": '<path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"/><rect x="8" y="2" width="8" height="4" rx="1" ry="1"/>',
    "award": '<circle cx="12" cy="8" r="7"/><polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"/>',
    "wallet": '<rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/>',
    "chart": '<line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>',
    "logout": '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>',
    "sun": '<circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>',
    "moon": '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>',
    "search": '<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>',
    "plus": '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
    "edit": '<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4z"/>',
    "trash": '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>',
    "eye": '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
    "download": '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
    "x": '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
    "check": '<polyline points="20 6 9 17 4 12"/>',
    "alert": '<path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
    "menu": '<line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/>',
    "grid": '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>',
}


@register.simple_tag
def icon(name: str, cls: str = "") -> str:
    path = _ICONS.get(name, _ICONS["grid"])
    return format_html(
        '<svg class="icon {}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" '
        'focusable="false">{}</svg>',
        cls,
        path,
    )


@register.inclusion_tag("common/_badge.html")
def badge(value: Any, tone: str | None = None) -> dict[str, str]:
    if tone is None:
        tone = _TONE_BY_VALUE.get(str(value).strip().lower(), "neutral")
    return {"value": str(value), "tone": tone}


@register.filter
def currency(value: Any) -> str:
    if value in (None, ""):
        return "—"
    try:
        amount = decimal.Decimal(str(value))
    except (decimal.InvalidOperation, ValueError, TypeError):
        return "—"
    return f"{settings.CURRENCY_CODE} {number_format(amount, decimal_pos=2)}"


@register.filter
def lookup(obj: Any, path: str) -> Any:
    """Resolve a dotted attribute path on an object (template-table helper)."""
    current: Any = obj
    for part in path.split("__"):
        if current is None or part.startswith("_"):
            return ""
        try:
            current = getattr(current, part)
        except (AttributeError, TypeError):
            return ""
        if callable(current):
            current = current()
    return current


@register.simple_tag(takes_context=True)
def json_data(context: Any, value: Any, element_id: str) -> str:
    """Serialise data for client scripts inside a nonce'd JSON block."""
    import json

    from django.core.serializers.json import DjangoJSONEncoder
    from django.utils.html import format_html
    from django.utils.safestring import mark_safe

    request = context["request"]
    attrs = (
        format_html(' nonce="{}"', request.csp_nonce) if getattr(request, "csp_nonce", "") else ""
    )
    payload = mark_safe(  # noqa: S308 - JSON escapes <, > and & before use
        json.dumps(value, cls=DjangoJSONEncoder)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return format_html(
        '<script type="application/json" id="{id}"{attrs}>{payload}</script>',
        id=element_id,
        attrs=attrs,
        payload=payload,
    )


@register.inclusion_tag("common/_form_field.html")
def form_field(field: Any) -> dict[str, Any]:
    is_checkbox = isinstance(field.field.widget, django_forms.CheckboxInput)
    widget_cls = "form-check-input" if is_checkbox else "form-control"
    return {
        "field": field,
        "is_checkbox": is_checkbox,
        "widget_cls": widget_cls,
        "invalid": bool(field.errors),
    }


@register.simple_tag
def pct(value: Any) -> str:
    try:
        number = decimal.Decimal(str(value))
    except (decimal.InvalidOperation, ValueError, TypeError):
        return "—"
    return f"{number.quantize(decimal.Decimal('0.1'))}%"


@register.simple_tag(takes_context=True)
def querystring(context: Any, **overrides: Any) -> str:
    """Current query string with overrides; empty overrides pop a parameter."""
    from urllib.parse import urlencode

    params: dict[str, str] = dict(context["request"].GET.items())
    for key, value in overrides.items():
        if value in (None, ""):
            params.pop(key, None)
        else:
            params[key] = str(value)
    encoded = urlencode(params)
    return f"?{encoded}" if encoded else "?"


@register.simple_tag
def paginator_window(page_obj: Any) -> range | list[int]:
    """Neighbour pages (±2) for list pagination."""
    number = page_obj.number
    total = page_obj.paginator.num_pages
    return range(max(number - 2, 1), min(number + 2, total) + 1)


def render_template(name: str, context: dict[str, Any]) -> str:
    return render_to_string(name, context)
