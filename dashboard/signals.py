"""Version bump signals: any write to domain data invalidates cached stats."""

from django.apps import apps
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from dashboard.caching import bump

_WATCHED = [
    ("students", "Student"),
    ("students", "Enrollment"),
    ("attendance", "Attendance"),
    ("attendance", "Policy"),
    ("results", "Result"),
    ("billing", "Invoice"),
    ("billing", "Payment"),
    ("academics", "Exam"),
    ("academics", "Group"),
    ("accounts", "GroupAssignment"),
    ("accounts", "User"),
]


@receiver(post_save, dispatch_uid="dashboard_cache_bump_save")
@receiver(post_delete, dispatch_uid="dashboard_cache_bump_delete")
def _bump(sender, **kwargs) -> None:
    from dashboard.signals import _WATCHED

    if sender._meta.label in {f"{app}.{model}" for app, model in _WATCHED}:
        bump()


def connect() -> None:
    for app_label, model_name in _WATCHED:
        apps.get_model(app_label, model_name)
