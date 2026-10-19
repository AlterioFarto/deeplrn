import factory

from billing.models import Invoice, Payment


class InvoiceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Invoice

    student = factory.SubFactory("students.factories.StudentFactory")
    period_start = "2025-01-01"
    period_end = "2025-01-31"
    amount_due = "500.00"
    due_date = "2025-01-31"
    status = Invoice.Status.ISSUED


class PaymentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Payment

    invoice = factory.SubFactory(InvoiceFactory)
    amount = "500.00"
    paid_on = "2025-01-31"
    method = Payment.Method.CASH
    receipt_no = factory.Sequence(lambda n: f"RCPT-{n:05d}")
    recorded_by = factory.SubFactory("accounts.factories.AdminUserFactory")
