"""
Billing CRUD views for the clinic dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.billing.models import Invoice, InvoiceItem, Payment, ServiceCatalog


class BillingListView(View):
    """List all invoices."""

    def get(self, request):
        invoices = Invoice.objects.select_related("patient").prefetch_related("payments")

        status = request.GET.get("status")
        if status:
            invoices = invoices.filter(status=status)

        context = {
            "invoices": invoices[:100],
            "status_choices": Invoice.STATUS_CHOICES,
            "selected_status": status or "",
            "total": invoices.count(),
        }
        return render(request, "dashboard/billing/list.html", context)


class BillingCreateView(View):
    """Create a new invoice."""

    def get(self, request):
        from apps.patients.models import Patient
        context = {
            "patients": Patient.objects.all()[:200],
            "services": ServiceCatalog.objects.filter(is_active=True),
        }
        return render(request, "dashboard/billing/form.html", context)

    def post(self, request):
        from apps.patients.models import Patient
        patient_id = request.POST.get("patient")
        notes = request.POST.get("notes", "").strip()

        patient = None
        if patient_id:
            patient = Patient.objects.filter(pk=patient_id).first()

        invoice = Invoice.objects.create(
            patient=patient,
            notes=notes,
            created_by=request.user,
        )

        # Parse line items
        descriptions = request.POST.getlist("item_desc")
        quantities = request.POST.getlist("item_qty")
        prices = request.POST.getlist("item_price")

        subtotal = 0
        for desc, qty, price in zip(descriptions, quantities, prices):
            if desc.strip() and qty and price:
                item = InvoiceItem.objects.create(
                    invoice=invoice,
                    description=desc.strip(),
                    quantity=int(qty or 1),
                    unit_price=float(price or 0),
                )
                subtotal += item.total

        invoice.subtotal = subtotal
        invoice.grand_total = subtotal
        invoice.save()

        return redirect("/billing/")


class BillingDetailView(View):
    """View invoice detail and collect payment."""

    def get(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        context = {
            "invoice": invoice,
            "items": invoice.items.all(),
            "payments": invoice.payments.all(),
            "paid_total": sum(p.amount for p in invoice.payments.all()),
            "methods": Payment.METHOD_CHOICES,
        }
        return render(request, "dashboard/billing/detail.html", context)

    def post(self, request, pk):
        invoice = get_object_or_404(Invoice, pk=pk)
        action = request.POST.get("action")

        if action == "pay":
            amount = float(request.POST.get("amount", 0))
            method = request.POST.get("method", "CASH")
            ref = request.POST.get("transaction_ref", "")

            if amount > 0:
                Payment.objects.create(
                    invoice=invoice,
                    amount=amount,
                    method=method,
                    transaction_ref=ref,
                    received_by=request.user,
                )

                paid = sum(p.amount for p in invoice.payments.all())
                if paid >= invoice.grand_total:
                    invoice.status = "PAID"
                else:
                    invoice.status = "PARTIALLY_PAID"
                invoice.save()

        return redirect(f"/billing/{pk}/")
