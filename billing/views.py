"""Billing views; guardians see only their linked students' invoices."""

from typing import Any

from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    FormView,
    ListView,
    UpdateView,
    View,
)

from academics.models import Group
from billing import services
from billing.forms import InvoiceForm, PaymentForm
from billing.models import Invoice, Payment
from billing.selectors import invoice_detail_qs, invoice_list_qs
from common.exceptions import ServiceError
from common.mixins import BreadcrumbMixin, ListWorkflowMixin, RoleRequiredMixin, ScopedAccessMixin
from common.roles import Role
from common.scoping import scoped_queryset

ALL_ROLES = frozenset({Role.ADMIN, Role.MENTOR, Role.GUARDIAN})
STAFF_ROLES = frozenset({Role.ADMIN, Role.MENTOR})
ADMIN_ONLY = frozenset({Role.ADMIN})


class InvoiceListView(RoleRequiredMixin, ListWorkflowMixin, ListView):
    model = Invoice
    template_name = "common/object_list.html"
    allowed_roles = ALL_ROLES
    search_fields = ["student__first_name", "student__last_name", "student__admission_no"]
    filter_params = {"status": "status", "group": "student__group_id"}
    sort_fields = {"due": "due_date", "amount": "amount_due"}
    default_sort = "-due_date"
    columns = [
        ("Student", "student__full_name", "link"),
        ("Group", "student__group__name"),
        ("Period", "period_start", "date"),
        ("Amount due", "amount_due", "currency"),
        ("Paid", "paid_total", "currency"),
        ("Outstanding", "outstanding", "currency"),
        ("Due date", "due_date", "date"),
        ("Status", "status", "badge"),
    ]
    export_name = "invoices"
    page_title = "Invoices"
    empty_message = "No invoices match the current filters."
    breadcrumbs = [("Invoices", None)]

    def get_queryset(self):
        return invoice_list_qs(
            user=self.current_user(),
            q=self.request.GET.get("q", "").strip() or None,
            status=self.request.GET.get("status") or None,
        )

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        hide_group = self.current_user().role == Role.GUARDIAN
        columns = context["columns"]
        if hide_group:
            columns = [c for c in columns if c["path"] != "student__group__name"]
        context.update(
            page_title=self.page_title,
            empty_message=self.empty_message,
            row_url_name="billing:invoice_detail",
            columns=columns,
            filter_form_url=reverse("billing:invoice_list"),
            status_choices=Invoice.Status.choices,
            group_choices=(
                None if hide_group else [(g.pk, str(g)) for g in Group.objects.order_by("name")]
            ),
        )
        if self.current_user().role in STAFF_ROLES:
            context.update(create_url=reverse("billing:invoice_create"), create_label="Add invoice")
        return context


class InvoiceCreateView(RoleRequiredMixin, BreadcrumbMixin, CreateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    page_title = "Add invoice"
    submit_label = "Create invoice"
    success_url = reverse_lazy("billing:invoice_list")
    breadcrumbs = [("Invoices", reverse_lazy("billing:invoice_list")), ("Add invoice", None)]

    def get_form_kwargs(self) -> dict[str, Any]:
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.current_user()
        return kwargs

    def form_valid(self, form: InvoiceForm) -> Any:
        cleaned = form.cleaned_data
        try:
            services.create_invoice(
                student=cleaned["student"],
                period_start=cleaned["period_start"],
                period_end=cleaned["period_end"],
                amount_due=cleaned["amount_due"],
                due_date=cleaned["due_date"],
                actor=self.current_user(),
            )
        except ServiceError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Invoice created.")
        return redirect(self.success_url)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title, submit_label=self.submit_label, cancel_url=self.success_url
        )
        return context


class InvoiceUpdateView(RoleRequiredMixin, ScopedAccessMixin, UpdateView):
    model = Invoice
    form_class = InvoiceForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    page_title = "Edit invoice"
    submit_label = "Save changes"
    breadcrumbs = [("Invoices", reverse_lazy("billing:invoice_list")), ("Edit invoice", None)]

    def get_queryset(self):
        return invoice_detail_qs(user=self.current_user())

    def form_valid(self, form: InvoiceForm) -> Any:
        cleaned = form.cleaned_data
        try:
            services.update_invoice(
                invoice=self.object,
                period_start=cleaned["period_start"],
                period_end=cleaned["period_end"],
                amount_due=cleaned["amount_due"],
                due_date=cleaned["due_date"],
                actor=self.current_user(),
            )
        except ServiceError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Invoice updated.")
        return redirect("billing:invoice_detail", pk=self.object.pk)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            submit_label=self.submit_label,
            cancel_url=reverse("billing:invoice_detail", args=[self.object.pk]),
        )
        return context


class InvoiceVoidView(RoleRequiredMixin, DeleteView):
    model = Invoice
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    context_object_name = "invoice"
    success_url = reverse_lazy("billing:invoice_list")
    page_title = "Void invoice"
    breadcrumbs = [("Invoices", reverse_lazy("billing:invoice_list")), ("Void", None)]

    def get_queryset(self):
        return invoice_detail_qs(user=self.current_user())

    def post(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        invoice = self.get_object()
        try:
            services.void_invoice(invoice=invoice, actor=self.current_user())
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect("billing:invoice_detail", pk=invoice.pk)
        messages.success(request, "Invoice voided.")
        return redirect(self.success_url)

    def get(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        invoice = self.get_object()
        return self._confirm_page(request, invoice)

    def _confirm_page(self, request: Any, invoice: Invoice) -> Any:
        from django.shortcuts import render

        return render(
            request,
            self.template_name,
            {
                "object": invoice,
                "page_title": self.page_title,
                "confirm_message": (
                    f"Void invoice for {invoice.student}? Voided invoices cannot receive payments; "
                    "the outstanding balance will become zero."
                ),
                "cancel_url": reverse("billing:invoice_detail", args=[invoice.pk]),
            },
        )


class InvoiceDetailView(RoleRequiredMixin, BreadcrumbMixin, DetailView):
    model = Invoice
    template_name = "billing/invoice_detail.html"
    context_object_name = "invoice"
    allowed_roles = ALL_ROLES
    breadcrumbs = [("Invoices", reverse_lazy("billing:invoice_list")), ("Detail", None)]

    def get_queryset(self):
        return invoice_detail_qs(user=self.current_user())

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        invoice = self.object
        context.update(
            page_title=f"Invoice - {invoice.student}",
            payments=[
                {
                    "id": payment.pk,
                    "amount": payment.amount,
                    "paid_on": payment.paid_on,
                    "method": payment.get_method_display(),
                    "receipt_no": payment.receipt_no,
                    "recorded_by": payment.recorded_by,
                    "is_deleted": payment.deleted_at is not None,
                    "delete_url": (
                        reverse("billing:payment_delete", args=[payment.pk])
                        if self.current_user().role == Role.ADMIN
                        else None
                    ),
                    "restore_url": (
                        reverse("billing:payment_restore", args=[payment.pk])
                        if self.current_user().role == Role.ADMIN
                        else None
                    ),
                }
                for payment in invoice.payments.all()
            ],
            outstanding=services.outstanding_for_invoice(invoice=invoice),
            can_record=self.current_user().role in STAFF_ROLES
            and invoice.status == Invoice.Status.ISSUED,
            payment_url=reverse("billing:payment_create", args=[invoice.pk]),
            issue_url=(
                reverse("billing:invoice_issue", args=[invoice.pk])
                if self.current_user().role in STAFF_ROLES
                and invoice.status == Invoice.Status.DRAFT
                else None
            ),
            void_url=(
                reverse("billing:invoice_void", args=[invoice.pk])
                if self.current_user().role == Role.ADMIN and invoice.status != Invoice.Status.VOID
                else None
            ),
            edit_url=(
                reverse("billing:invoice_update", args=[invoice.pk])
                if self.current_user().role in STAFF_ROLES
                and invoice.status == Invoice.Status.DRAFT
                else None
            ),
        )
        return context


class InvoiceIssueView(RoleRequiredMixin, View):
    http_method_names = ["post"]
    allowed_roles = STAFF_ROLES

    def post(self, request: Any, pk: int) -> Any:
        invoice = self._get_invoice(request, pk)
        try:
            services.issue_invoice(invoice=invoice, actor=self.current_user())
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect("billing:invoice_detail", pk=pk)
        messages.success(request, "Invoice issued.")
        return redirect("billing:invoice_detail", pk=pk)

    def _get_invoice(self, request: Any, pk: int) -> Invoice:
        invoice = invoice_detail_qs(user=self.current_user()).filter(pk=pk).first()
        if invoice is None:
            raise Http404("Invoice not found.")
        return invoice


class PaymentCreateView(RoleRequiredMixin, BreadcrumbMixin, FormView):
    form_class = PaymentForm
    template_name = "common/object_form.html"
    allowed_roles = STAFF_ROLES
    page_title = "Record payment"
    submit_label = "Record payment"
    breadcrumbs = [("Invoices", reverse_lazy("billing:invoice_list")), ("Record payment", None)]

    def _get_invoice(self, request: Any) -> Invoice:
        invoice_pk = self.kwargs["invoice_pk"]
        invoice = invoice_detail_qs(user=self.current_user()).filter(pk=invoice_pk).first()
        if invoice is None:
            raise Http404("Invoice not found.")
        return invoice

    def get_success_url(self) -> str:
        return reverse("billing:invoice_detail", args=[self.kwargs["invoice_pk"]])

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        invoice = self._get_invoice(self.request)
        context.update(
            page_title=f"{self.page_title} - {invoice}",
            submit_label=self.submit_label,
            cancel_url=self.get_success_url(),
            outstanding=services.outstanding_for_invoice(invoice=invoice),
        )
        return context

    def form_valid(self, form: PaymentForm) -> Any:
        cleaned = form.cleaned_data
        try:
            services.record_payment(
                invoice=self._get_invoice(self.request),
                amount=cleaned["amount"],
                paid_on=cleaned["paid_on"],
                method=cleaned["method"],
                receipt_no=cleaned["receipt_no"],
                notes=cleaned.get("notes", ""),
                recorded_by=self.current_user(),
                actor=self.current_user(),
            )
        except ServiceError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Payment recorded.")
        return redirect(self.get_success_url())


class PaymentDeleteView(RoleRequiredMixin, DeleteView):
    model = Payment
    template_name = "common/object_confirm_delete.html"
    allowed_roles = ADMIN_ONLY
    context_object_name = "payment"
    success_url = reverse_lazy("billing:invoice_list")
    page_title = "Reverse payment"

    def get_queryset(self):
        return scoped_queryset(
            Payment.objects.select_related("invoice__student"), self.current_user()
        )

    def form_valid(self, form: Any) -> Any:
        try:
            services.delete_payment(payment=self.object, actor=self.current_user())
        except ServiceError as exc:
            messages.error(self.request, str(exc))
            return redirect("billing:invoice_detail", pk=self.object.invoice_id)
        messages.success(
            self.request, "Payment reversed. The invoice outstanding balance has been recalculated."
        )
        return redirect("billing:invoice_detail", pk=self.object.invoice_id)

    def get_context_data(self, **kwargs: Any) -> dict[str, Any]:
        context = super().get_context_data(**kwargs)
        context.update(
            page_title=self.page_title,
            confirm_message=(
                f"Remove payment {self.object}? The student's outstanding balance will "
                "come back automatically. This is recorded in the audit log."
            ),
            cancel_url=reverse("billing:invoice_detail", args=[self.object.invoice_id]),
        )
        return context


class PaymentRestoreView(RoleRequiredMixin, View):
    http_method_names = ["post"]
    allowed_roles = ADMIN_ONLY

    def post(self, request: Any, pk: int) -> Any:
        payment = (
            scoped_queryset(Payment.all_objects.select_related("invoice"), self.current_user())
            .filter(pk=pk)
            .first()
        )
        if payment is None or payment.deleted_at is None:
            raise Http404("Payment not found.")
        try:
            services.restore_payment(payment=payment, actor=self.current_user())
        except ServiceError as exc:
            messages.error(request, str(exc))
            return redirect("billing:invoice_detail", pk=payment.invoice_id)
        messages.success(request, "Payment restored.")
        return redirect("billing:invoice_detail", pk=payment.invoice_id)
