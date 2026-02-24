# apps/labs/template_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.db.models import Sum, Count
from .models import LabTest, LabOrder, LabResult, LabSample
from apps.patients.models import Patient

class LabTestCatalogView(View):
    """Manage the catalog of laboratory tests."""
    template_name = "categories/labs_catalog.html"

    def get(self, request):
        tests = LabTest.objects.all().order_by('name')
        context = {
            "tests": tests,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        category = request.POST.get('category', '').strip()
        price = request.POST.get('price', '0')
        range_val = request.POST.get('reference_range', '').strip()

        try:
            LabTest.objects.create(
                name=name,
                code=code,
                category=category,
                price=float(price),
                reference_range=range_val
            )
            return redirect(f"{request.path}?success=Test added successfully")
        except Exception as e:
            tests = LabTest.objects.all().order_by('name')
            return render(request, self.template_name, {
                "tests": tests,
                "error_message": str(e)
            })

class LabOrderListView(View):
    """List lab orders and create new ones."""
    template_name = "categories/labs_orders.html"

    def get(self, request):
        orders = LabOrder.objects.select_related('patient', 'doctor').all().order_by('-ordered_at')
        patients = Patient.objects.all()
        tests = LabTest.objects.filter(is_active=True)
        context = {
            "orders": orders,
            "patients": patients,
            "tests": tests,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        patient_id = request.POST.get('patient_id')
        test_ids = request.POST.getlist('tests')
        priority = request.POST.get('priority', 'ROUTINE')
        notes = request.POST.get('notes', '').strip()

        try:
            patient = Patient.objects.get(id=patient_id)
            order = LabOrder.objects.create(
                patient=patient,
                doctor=request.user if request.user.is_authenticated else None,
                priority=priority,
                notes=notes
            )
            if test_ids:
                order.tests.set(test_ids)
            
            return redirect(f"{request.path}?success=Order created successfully")
        except Exception as e:
            orders = LabOrder.objects.select_related('patient', 'doctor').all().order_by('-ordered_at')
            patients = Patient.objects.all()
            tests = LabTest.objects.filter(is_active=True)
            return render(request, self.template_name, {
                "orders": orders,
                "patients": patients,
                "tests": tests,
                "error_message": str(e)
            })

class LabOrderEntryView(View):
    """View details of a lab order and enter results."""
    template_name = "categories/labs_order_entry.html"

    def get(self, request, order_id):
        order = LabOrder.objects.get(id=order_id)
        context = {
            "order": order,
            "results": order.results.all(),
            "tests": order.tests.all()
        }
        return render(request, self.template_name, context)

    def post(self, request, order_id):
        order = LabOrder.objects.get(id=order_id)
        action = request.POST.get('action')

        if action == "collect_sample":
            sample_type = request.POST.get('sample_type')
            LabSample.objects.create(
                order=order,
                sample_type=sample_type,
                collected_at=timezone.now(),
                collected_by=request.user if request.user.is_authenticated else None
            )
            order.status = 'COLLECTED'
            order.save()
        
        elif action == "enter_results":
            for test in order.tests.all():
                value = request.POST.get(f"result_{test.id}")
                is_abnormal = request.POST.get(f"abnormal_{test.id}") == "on"
                if value:
                    LabResult.objects.update_or_create(
                        order=order,
                        test=test,
                        defaults={
                            'value': value,
                            'is_abnormal': is_abnormal,
                            'recorded_by': request.user if request.user.is_authenticated else None
                        }
                    )
            order.status = 'COMPLETED'
            order.save()

        return redirect('lab-order-entry', order_id=order_id)
