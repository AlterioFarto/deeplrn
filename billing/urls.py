from django.urls import path

from billing import views

app_name = "billing"

urlpatterns = [
    path("invoices/", views.InvoiceListView.as_view(), name="invoice_list"),
    path("invoices/new/", views.InvoiceCreateView.as_view(), name="invoice_create"),
    path("invoices/<int:pk>/", views.InvoiceDetailView.as_view(), name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views.InvoiceUpdateView.as_view(), name="invoice_update"),
    path("invoices/<int:pk>/issue/", views.InvoiceIssueView.as_view(), name="invoice_issue"),
    path("invoices/<int:pk>/void/", views.InvoiceVoidView.as_view(), name="invoice_void"),
    path(
        "invoices/<int:invoice_pk>/payments/new/",
        views.PaymentCreateView.as_view(),
        name="payment_create",
    ),
    path("payments/<int:pk>/delete/", views.PaymentDeleteView.as_view(), name="payment_delete"),
    path("payments/<int:pk>/restore/", views.PaymentRestoreView.as_view(), name="payment_restore"),
]
