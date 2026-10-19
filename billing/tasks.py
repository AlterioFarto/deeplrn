"""Background jobs: monthly invoice generation (Celery)."""

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone


@shared_task
def generate_monthly_invoices() -> dict:
    """Create DRAFT invoices for the previous month, idempotent per student."""
    from billing.models import Invoice
    from students.models import Student

    today = timezone.localdate()
    first_of_month = today.replace(day=1)
    last_month_end = first_of_month - timedelta(days=1)
    period_start = last_month_end.replace(day=1)
    amount = settings.MONTHLY_INVOICE_AMOUNT

    created = 0
    skipped = 0
    for student in Student.objects.filter(deleted_at__isnull=True, is_active=True).order_by("pk"):
        try:
            with transaction.atomic():
                Invoice.objects.create(
                    student=student,
                    period_start=period_start,
                    period_end=last_month_end,
                    amount_due=amount,
                    due_date=last_month_end,
                    status=Invoice.Status.DRAFT,
                )
            created += 1
        except IntegrityError:
            skipped += 1
    return {
        "period_start": period_start.isoformat(),
        "created": created,
        "skipped": skipped,
    }
