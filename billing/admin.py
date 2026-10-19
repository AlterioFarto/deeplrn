from django.contrib import admin

from billing.models import Invoice, Payment


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("student", "period_start", "period_end", "amount_due", "due_date", "status")
    list_filter = ("status", "due_date")
    search_fields = ("student__first_name", "student__last_name", "student__admission_no")
    autocomplete_fields = ("student",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "receipt_no",
        "invoice",
        "amount",
        "paid_on",
        "method",
        "recorded_by",
        "deleted_at",
    )
    list_filter = ("method", "deleted_at")
    search_fields = ("receipt_no", "invoice__student__first_name", "invoice__student__last_name")
    autocomplete_fields = ("invoice", "recorded_by")
