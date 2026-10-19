"""Explicit audit hooks called from services inside their transactions."""

from typing import Any

from django.db import models

from common.context import get_request_id
from common.models import AuditLog
from common.roles import AuditAction


def snapshot(instance: models.Model, fields: tuple[str, ...]) -> dict[str, Any]:
    return {f: getattr(instance, f) for f in fields}


def make_diff(
    before: dict[str, Any], instance: models.Model, fields: tuple[str, ...]
) -> dict[str, list[Any]]:
    after = snapshot(instance, fields)
    return {f: [before[f], after[f]] for f in fields if before[f] != after[f]}


def log_action(
    *,
    action: AuditAction | str,
    actor: Any = None,
    obj: models.Model | None = None,
    diff: dict[str, Any] | None = None,
) -> None:
    """Record an audit entry. Must be called inside the service transaction."""
    AuditLog.objects.create(
        actor=actor if getattr(actor, "is_authenticated", False) else None,
        actor_email=getattr(actor, "email", "") or "",
        action=str(action),
        object_type=obj._meta.label if obj is not None else "",
        object_id=str(obj.pk) if obj is not None else "",
        object_repr=str(obj)[:255] if obj is not None else "",
        diff=diff or {},
        request_id=get_request_id(),
    )
