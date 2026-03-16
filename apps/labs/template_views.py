# apps/labs/template_views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.db.models import Sum, Count
from .models import LabTest, LabTestParameter, LabTestPackage, LabOrder, LabResult, LabSample, LabOrderAuditLog
from apps.patients.models import Patient
from apps.billing.models import Invoice, InvoiceItem
from apps.notifications.models import Notification
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.inventory.models import InventoryItem, InventoryBatch, StockTransaction, ItemType

class LabTestCatalogView(View):
    """Manage the catalog of laboratory tests."""
    template_name = "categories/labs_catalog.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_view_catalog')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access to Lab Catalog')
        
        tests = LabTest.objects.prefetch_related('parameters').all().order_by('name')
        packages = LabTestPackage.objects.prefetch_related('tests').all().order_by('name')
        context = {
            "tests": tests,
            "packages": packages,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        action = request.POST.get('action', 'create_test')

        if action == 'delete_test':
            test_id = request.POST.get('test_id')
            try:
                LabTest.objects.filter(id=test_id).delete()
                return redirect(f"{request.path}?success=Test deleted successfully")
            except Exception as e:
                return redirect(f"{request.path}?error={e}")

        if action == 'delete_package':
            package_id = request.POST.get('package_id')
            try:
                LabTestPackage.objects.filter(id=package_id).delete()
                return redirect(f"{request.path}?success=Package deleted successfully")
            except Exception as e:
                return redirect(f"{request.path}?error={e}")

        if action in ['create_package', 'edit_package']:
            name = request.POST.get('package_name', '').strip()
            desc = request.POST.get('package_desc', '').strip()
            price = request.POST.get('package_price', '0')
            discount = request.POST.get('package_discount', '0')
            test_ids = request.POST.getlist('package_tests')
            
            try:
                if action == 'edit_package':
                    package_id = request.POST.get('package_id')
                    pkg = LabTestPackage.objects.get(id=package_id)
                    pkg.name = name
                    pkg.description = desc
                    pkg.price = float(price)
                    pkg.discount_percentage = float(discount)
                    pkg.save()
                else:
                    pkg = LabTestPackage.objects.create(
                        name=name, description=desc,
                        price=float(price), discount_percentage=float(discount)
                    )
                
                pkg.tests.set(test_ids)
                
                if action == 'edit_package':
                    return redirect(f"{request.path}?success=Package updated successfully")
                else:
                    return redirect(f"{request.path}?success=Package created successfully")
            except Exception as e:
                return redirect(f"{request.path}?error={e}")

        # Common field extraction for create/edit tests
        name = request.POST.get('name', '').strip()
        code = request.POST.get('code', '').strip()
        category = request.POST.get('category', '').strip()
        price = request.POST.get('price', '0')
        range_val = request.POST.get('reference_range', '').strip()
        sample_type = request.POST.get('sample_type', '').strip()
        prep = request.POST.get('preparation_instructions', '').strip()
        turnaround = request.POST.get('turnaround_time', '').strip()

        try:
            if action == 'edit_test':
                test_id = request.POST.get('test_id')
                test = LabTest.objects.get(id=test_id)
                test.name = name
                test.code = code
                test.category = category
                test.price = float(price)
                test.reference_range = range_val
                test.sample_type = sample_type
                test.preparation_instructions = prep
                test.turnaround_time = turnaround
                test.save()
            else:
                test = LabTest.objects.create(
                    name=name, code=code, category=category,
                    price=float(price), reference_range=range_val,
                    sample_type=sample_type, preparation_instructions=prep,
                    turnaround_time=turnaround
                )

            # Handle parameters
            param_ids = request.POST.getlist('param_id[]')
            param_names = request.POST.getlist('param_name[]')
            param_units = request.POST.getlist('param_unit[]')
            param_lows = request.POST.getlist('param_low[]')
            param_highs = request.POST.getlist('param_high[]')

            # Delete parameters not in the submitted list
            current_param_ids = [int(pid) for pid in param_ids if pid.isdigit()]
            test.parameters.exclude(id__in=current_param_ids).delete()

            for i, p_name in enumerate(param_names):
                if not p_name.strip(): continue
                unit = param_units[i] if i < len(param_units) else ''
                low = param_lows[i] if i < len(param_lows) else ''
                high = param_highs[i] if i < len(param_highs) else ''
                pid = param_ids[i] if i < len(param_ids) else ''

                if pid and pid.isdigit():
                    p = LabTestParameter.objects.get(id=pid, test=test)
                    p.name = p_name.strip()
                    p.unit = unit.strip()
                    p.normal_low = low.strip()
                    p.normal_high = high.strip()
                    p.save()
                else:
                    LabTestParameter.objects.create(
                        test=test, name=p_name.strip(), unit=unit.strip(),
                        normal_low=low.strip(), normal_high=high.strip()
                    )

            if action == 'edit_test':
                return redirect(f"{request.path}?success=Test updated successfully")
            else:
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
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_view_orders')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access to Lab Orders')
        
        orders = LabOrder.objects.select_related('patient', 'doctor', 'technician').all().order_by('-ordered_at')
        
        # Status filtering
        status_filter = request.GET.get('status', '')
        if status_filter and status_filter != 'ALL':
            orders = orders.filter(status=status_filter)
        
        # Count per status for tab badges
        all_count = LabOrder.objects.count()
        status_counts = {
            'PENDING': LabOrder.objects.filter(status='PENDING').count(),
            'COLLECTED': LabOrder.objects.filter(status='COLLECTED').count(),
            'PROCESSING': LabOrder.objects.filter(status='PROCESSING').count(),
            'COMPLETED': LabOrder.objects.filter(status__in=['COMPLETED', 'REPORT_UPLOADED']).count(),
        }
        
        patients = Patient.objects.all()
        tests = LabTest.objects.filter(is_active=True)
        packages = LabTestPackage.objects.filter(is_active=True)
        User = get_user_model()
        technicians = User.objects.filter(role__name__icontains='Lab') | User.objects.filter(is_superuser=True)
        
        context = {
            "orders": orders,
            "patients": patients,
            "tests": tests,
            "packages": packages,
            "technicians": technicians.distinct(),
            "status_filter": status_filter or 'ALL',
            "all_count": all_count,
            "status_counts": status_counts,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        patient_id = request.POST.get('patient_id')
        test_ids = request.POST.getlist('tests')
        priority = request.POST.get('priority', 'ROUTINE')
        notes = request.POST.get('notes', '').strip()
        technician_id = request.POST.get('technician_id')

        try:
            patient = Patient.objects.get(id=patient_id)
            order = LabOrder.objects.create(
                patient=patient,
                doctor=request.user if request.user.is_authenticated else None,
                technician_id=technician_id if technician_id else None,
                priority=priority,
                notes=notes
            )
            
            # Handle Packages first (so their package pricing applies)
            total_price = 0
            invoice_items_data = []
            added_test_ids = set()
            
            package_ids = request.POST.getlist('packages')
            for pkg_id in package_ids:
                try:
                    pkg = LabTestPackage.objects.get(id=pkg_id)
                    for test in pkg.tests.all():
                        added_test_ids.add(test.id)
                    
                    invoice_items_data.append({
                        'desc': f"Lab Package: {pkg.name}",
                        'price': pkg.price
                    })
                    total_price += pkg.price
                except LabTestPackage.DoesNotExist:
                    continue

            # Add selected individual tests to the order
            for test_id in test_ids:
                if test_id.isdigit() and int(test_id) not in added_test_ids:
                    try:
                        test = LabTest.objects.get(id=test_id)
                        added_test_ids.add(test.id)
                        invoice_items_data.append({
                            'desc': f"Lab Test: {test.name}",
                            'price': test.price
                        })
                        total_price += test.price
                    except LabTest.DoesNotExist:
                        continue
            
            if added_test_ids:
                tests_to_add = LabTest.objects.filter(id__in=added_test_ids)
                order.tests.add(*tests_to_add)
            
            # Billing Integration
            if total_price > 0:
                # Find or create a DRAFT invoice for this patient today
                invoice = Invoice.objects.filter(
                    patient=patient, 
                    status='DRAFT',
                    created_at__date=timezone.now().date()
                ).first()
                
                if not invoice:
                    invoice = Invoice.objects.create(
                        patient=patient,
                        status='DRAFT',
                        created_by=request.user if request.user.is_authenticated else None,
                        notes=f"Auto-generated for Lab Order {order.id.hex[:8].upper()}"
                    )
                
                # Add tests as invoice items
                for item_data in invoice_items_data:
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=item_data['desc'],
                        quantity=1,
                        unit_price=item_data['price']
                    )
                
                # Update invoice totals
                invoice_items = invoice.items.all()
                invoice.subtotal = sum(i.total for i in invoice_items)
                invoice.grand_total = invoice.subtotal
                invoice.save()

            return redirect('/categories/labs/orders/?success=Order created and billed successfully')
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
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_enter_results')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/categories/labs/orders/?error=Unauthorized to enter results')
        
        order = LabOrder.objects.get(id=order_id)
        can_approve = False
        if request.user.is_superuser or request.user.has_permission('clinics.manage') or getattr(request.user.role, 'name', '') == 'Doctor':
            can_approve = True

        context = {
            "order": order,
            "results": order.results.all(),
            "tests": order.tests.all(),
            "can_approve": can_approve,
            "audit_logs": order.audit_logs.all()
        }
        return render(request, self.template_name, context)

    def post(self, request, order_id):
        order = LabOrder.objects.get(id=order_id)
        action = request.POST.get('action')

        if action == "collect_sample":
            sample_type = request.POST.get('sample_type')
            location = request.POST.get('location', '').strip()
            barcode = request.POST.get('barcode', '').strip() or f"LAB-{order.id.hex[:8].upper()}"
            
            LabSample.objects.create(
                order=order,
                sample_type=sample_type,
                collection_location=location,
                barcode=barcode,
                collected_at=timezone.now(),
                collected_by=request.user if request.user.is_authenticated else None
            )
            order.status = 'COLLECTED'
            order.save()

            LabOrderAuditLog.objects.create(
                order=order,
                user=request.user if request.user.is_authenticated else None,
                action="Sample Collected",
                details=f"Sample: {sample_type}, Barcode: {barcode}"
            )
        
        elif action == "start_processing":
            order.status = 'PROCESSING'
            order.save()

            LabOrderAuditLog.objects.create(
                order=order,
                user=request.user if request.user.is_authenticated else None,
                action="Processing Started",
                details="Technician moved order to laboratory processing floor."
            )
        
        elif action == "enter_results":
            report_file = request.FILES.get('pdf_report')
            if report_file:
                # Update order with the first result's test if needed or just store in a generic way
                # Usually we'd want to store it on the LabOrder or LabResult
                # Since models.py has pdf_report on LabResult, we might need a dummy or a main result
                order.status = 'REPORT_UPLOADED'
                order.save()

            for test in order.tests.prefetch_related('parameters').all():
                if test.parameters.exists():
                    for param in test.parameters.all():
                        value_str = request.POST.get(f"result_{test.id}_{param.id}")
                        is_abnormal = request.POST.get(f"abnormal_{test.id}_{param.id}") == "on"

                        if not is_abnormal and value_str and param.normal_low and param.normal_high:
                            try:
                                val = float(value_str)
                                low = float(param.normal_low)
                                high = float(param.normal_high)
                                if val < low or val > high:
                                    is_abnormal = True
                            except:
                                pass

                        if value_str:
                            res, created = LabResult.objects.update_or_create(
                                order=order,
                                test=test,
                                parameter=param,
                                defaults={
                                    'value': value_str,
                                    'unit': param.unit,
                                    'is_abnormal': is_abnormal,
                                    'recorded_by': request.user if request.user.is_authenticated else None
                                }
                            )
                            if report_file:
                                res.pdf_report = report_file
                                res.save()
                else:
                    value_str = request.POST.get(f"result_{test.id}")
                    is_abnormal = request.POST.get(f"abnormal_{test.id}") == "on"
                    
                    # Simple Auto-detect abnormal if not manually checked
                    if not is_abnormal and value_str and test.reference_range:
                        try:
                            # Try to parse numeric range like "12-16" or "< 5.0"
                            import re
                            val = float(value_str)
                            # Extract numbers from reference range
                            nums = re.findall(r"[-+]?\d*\.\d+|\d+", test.reference_range)
                            if len(nums) == 2:
                                low, high = float(nums[0]), float(nums[1])
                                if val < low or val > high:
                                    is_abnormal = True
                            elif len(nums) == 1:
                                if "<" in test.reference_range and val >= float(nums[0]):
                                    is_abnormal = True
                                elif ">" in test.reference_range and val <= float(nums[0]):
                                    is_abnormal = True
                        except:
                            pass

                    if value_str:
                        res, created = LabResult.objects.update_or_create(
                            order=order,
                            test=test,
                            parameter=None,
                            defaults={
                                'value': value_str,
                                'is_abnormal': is_abnormal,
                                'recorded_by': request.user if request.user.is_authenticated else None
                            }
                        )
                        if report_file:
                            res.pdf_report = report_file
                            res.save()

            if order.status != 'REPORT_UPLOADED':
                order.status = 'COMPLETED'
            order.save()

            LabOrderAuditLog.objects.create(
                order=order,
                user=request.user if request.user.is_authenticated else None,
                action="Results Entered",
                details="Values recorded for all test parameters."
            )

            # Trigger Notification for Doctor
            if order.doctor:
                Notification.objects.create(
                    user=order.doctor,
                    type=Notification.NotificationType.LAB,
                    title=f"Lab Results Ready: {order.patient.full_name}",
                    body=f"Results for order {order.id.hex[:8].upper()} are now available.",
                    action_url=f"/categories/labs/orders/{order.id}/report/"
                )

        elif action == "approve_results":
            # Doctor verifies results
            if request.user.has_permission('clinics.manage') or getattr(request.user.role, 'name', '') == 'Doctor' or request.user.is_superuser:
                order.status = 'VERIFIED'
                order.save()
                
                # Mark all results as verified
                now = timezone.now()
                for res in order.results.all():
                    res.verified_by = request.user
                    res.verified_at = now
                    res.save()
                
                LabOrderAuditLog.objects.create(
                    order=order,
                    user=request.user,
                    action="Results Verified",
                    details="Laboratory Doctor reviewed and approved all results."
                )
            else:
                return redirect(f'/categories/labs/orders/{order_id}/?error=Unauthorized to verify results')

        return redirect('lab-order-entry', order_id=order_id)

class LabOrderPrintSlipView(View):
    """Simple printable slip for a lab order."""
    template_name = "categories/labs_order_slip.html"

    def get(self, request, order_id):
        order = get_object_or_404(LabOrder, id=order_id)
        return render(request, self.template_name, {"order": order})

from django.template.loader import get_template
from django.http import HttpResponse

class LabReportView(View):
    """Official lab report view for doctors and patients."""
    template_name = "categories/labs_report.html"

    def get(self, request, order_id):
        order = get_object_or_404(LabOrder, id=order_id)
        results = order.results.select_related('test').all()
        context = {
            "order": order,
            "results": results
        }
        
        if request.GET.get('format') == 'html':
            return render(request, self.template_name, context)
            
        try:
            from xhtml2pdf import pisa
            template = get_template(self.template_name)
            html = template.render(context)
            response = HttpResponse(content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="lab_report_{order.id.hex[:8]}.pdf"'
            
            pisa_status = pisa.CreatePDF(html, dest=response)
            if pisa_status.err:
                return HttpResponse('We had some errors generating the PDF.')
            return response
        except ImportError:
            # Fallback to HTML if xhtml2pdf is not correctly installed
            return render(request, self.template_name, context)
        except Exception as e:
            return HttpResponse(f"Error generating PDF: {e}")

class LabSampleCollectionView(View):
    """Standalone page for listing orders pending sample collection."""
    template_name = "categories/labs_samples.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_view_orders')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access to Sample Collection')
        
        # Only show orders that are PENDING
        pending_orders = LabOrder.objects.select_related('patient', 'doctor').filter(status='PENDING').order_by('-ordered_at')
        
        context = {
            "orders": pending_orders,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # We handle collection from the list view directly via a modal/panel
        order_id = request.POST.get('order_id')
        sample_type = request.POST.get('sample_type')
        location = request.POST.get('location', '').strip()
        barcode = request.POST.get('barcode', '').strip()
        
        try:
            order = LabOrder.objects.get(id=order_id)
            if not barcode:
                barcode = f"LAB-{order.id.hex[:8].upper()}"
                
            LabSample.objects.create(
                order=order,
                sample_type=sample_type,
                collection_location=location,
                barcode=barcode,
                collected_at=timezone.now(),
                collected_by=request.user if request.user.is_authenticated else None
            )
            order.status = 'COLLECTED'
            order.save()
            return redirect('/categories/labs/samples/?success=Sample collected successfully')
        except Exception as e:
            return redirect(f'/categories/labs/samples/?error={str(e)}')


class LabProcessingView(View):
    """Panel for technicians to process tests and enter results."""
    template_name = "categories/labs_processing.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_enter_results')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access to Lab Processing')
        
        # Start with orders that are collected, processing, or completed
        orders = LabOrder.objects.select_related('patient', 'technician').filter(
            status__in=['COLLECTED', 'PROCESSING', 'COMPLETED', 'REPORT_UPLOADED']
        )

        # Filter to only assigned orders if the user is a technician and not a superuser/admin
        if not request.user.is_superuser and not request.user.has_permission('clinics.manage'):
            orders = orders.filter(technician=request.user)

        # Sort with processing first, collected, then others
        from django.db.models import Case, When, Value, IntegerField
        orders = orders.annotate(
            status_order=Case(
                When(status='PROCESSING', then=Value(1)),
                When(status='COLLECTED', then=Value(2)),
                When(status='COMPLETED', then=Value(3)),
                When(status='REPORT_UPLOADED', then=Value(4)),
                default=Value(5),
                output_field=IntegerField(),
            )
        ).order_by('status_order', '-ordered_at')
        
        context = {
            "orders": orders,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta

class LabAnalyticsView(View):
    """Analytics dashboard for the lab module."""
    template_name = "categories/labs_analytics.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('lab_view_analytics')
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access')

        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        # 1. Total Tests (Orders)
        total_orders_today = LabOrder.objects.filter(ordered_at__gte=today_start).count()
        total_orders_week = LabOrder.objects.filter(ordered_at__gte=week_start).count()
        total_orders_month = LabOrder.objects.filter(ordered_at__gte=month_start).count()

        # 2. Revenue (Approximated from completed order items)
        def calc_revenue(orders):
            # Sum price of tests and packages associated with these orders
            # Simplified for now: just sum test prices in orders. 
            # Real revenue should look at InvoiceItem but this is a lab-centric view.
            revenue = 0
            for o in orders:
                revenue += sum(t.price for t in o.tests.all())
            return revenue

        completed_today = LabOrder.objects.filter(status='COMPLETED', updated_at__gte=today_start)
        completed_week = LabOrder.objects.filter(status='COMPLETED', updated_at__gte=week_start)
        completed_month = LabOrder.objects.filter(status='COMPLETED', updated_at__gte=month_start)

        revenue_today = calc_revenue(completed_today)
        revenue_week = calc_revenue(completed_week)
        revenue_month = calc_revenue(completed_month)

        # 3. Technician Performance
        tech_performance = LabOrder.objects.filter(
            status__in=['COMPLETED', 'REPORT_UPLOADED', 'VERIFIED']
        ).values('technician__username', 'technician__first_name', 'technician__last_name').annotate(
            completed_count=Count('id')
        ).exclude(technician__isnull=True).order_by('-completed_count')[:5]

        # 4. Most Performed Tests
        top_tests = LabTest.objects.annotate(
            order_count=Count('orders', filter=Q(orders__status__in=['COMPLETED', 'REPORT_UPLOADED', 'VERIFIED']))
        ).order_by('-order_count')[:5]

        # 5. Cancelled Rate (Proxy for rejection rate)
        total_orders = LabOrder.objects.count()
        cancelled_orders = LabOrder.objects.filter(status='CANCELLED').count()
        rejection_rate = (cancelled_orders / total_orders * 100) if total_orders > 0 else 0

        context = {
            'metrics': {
                'today_orders': total_orders_today,
                'week_orders': total_orders_week,
                'month_orders': total_orders_month,
                'today_revenue': revenue_today,
                'week_revenue': revenue_week,
                'month_revenue': revenue_month,
                'rejection_rate': round(rejection_rate, 1),
            },
            'tech_performance': tech_performance,
            'top_tests': top_tests,
        }

        return render(request, self.template_name, context)

# Lab Inventory models are deprecated in favor of apps.inventory models
from django.db import transaction

class LabInventoryView(View):
    """Manage lab reagents and consumables via Global Inventory."""
    template_name = "categories/labs_inventory.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access to Inventory')

        search = request.GET.get('search', '').strip()
        
        # Filter global inventory for lab items
        items = InventoryItem.objects.filter(
            item_type__code__in=['LAB_REAGENT', 'LAB_TEST_KIT', 'CONSUMABLE', 'EQUIPMENT']
        ).order_by('name')
        
        if search:
            items = items.filter(Q(name__icontains=search) | Q(sku__icontains=search))

        # Annotate items with alerts
        now_date = timezone.now().date()
        low_stock_count = 0
        expiry_count = 0
        
        for item in items:
            item.is_low_stock = item.total_stock <= (item.min_stock_level or 0)
            if item.is_low_stock:
                low_stock_count += 1
                
            item.is_expiring_soon = False
            item.is_expired = False
            
            # Use total_stock and nearest expiry from batches
            batch = item.batches.filter(quantity__gt=0).order_by('expiry_date').first()
            if batch and batch.expiry_date:
                days_to_expiry = (batch.expiry_date - now_date).days
                if days_to_expiry < 0:
                    item.is_expired = True
                    expiry_count += 1
                elif days_to_expiry <= 30:
                    item.is_expiring_soon = True
                    expiry_count += 1
                item.expiry_date = batch.expiry_date
            else:
                item.expiry_date = None

        return render(request, self.template_name, {
            "items": items,
            "low_stock_count": low_stock_count,
            "expiry_count": expiry_count,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        })

    def post(self, request):
        if not request.user.is_superuser and not request.user.has_permission('clinics.manage'):
            return redirect('/dashboard/?error=Unauthorized')

        action = request.POST.get('action')
        
        try:
            with transaction.atomic():
                if action == 'add_item':
                    type_code = request.POST.get('category', 'LAB_REAGENT')
                    # Legacy mapping
                    if type_code == 'REAGENT': type_code = 'LAB_REAGENT'
                    if type_code == 'OTHER': type_code = 'GENERAL'
                    
                    item_type = ItemType.objects.get(code=type_code)
                    
                    item = InventoryItem.objects.create(
                        name=request.POST.get('name'),
                        sku=request.POST.get('sku', ''),
                        item_type=item_type,
                        unit=request.POST.get('unit', 'units'),
                        min_stock_level=request.POST.get('reorder_level', 10),
                    )
                    
                    initial_qty = float(request.POST.get('quantity_in_stock', 0))
                    if initial_qty > 0:
                        InventoryBatch.objects.create(
                            item=item,
                            batch_number=f"INIT-{item.sku or item.id}",
                            quantity=initial_qty,
                            expiry_date=request.POST.get('expiry_date') or None
                        )
                        item.total_stock = initial_qty
                        item.save()
                        
                        StockTransaction.objects.create(
                            item=item,
                            transaction_type='IN',
                            quantity=initial_qty,
                            performed_by=request.user,
                            notes="Initial stock entry"
                        )
                    return redirect('/categories/labs/inventory/?success=Item added successfully.')

                elif action == 'transaction':
                    item_id = request.POST.get('item_id')
                    trans_type = request.POST.get('transaction_type') # ADD, CONSUME, ADJUST
                    type_map = {'ADD': 'IN', 'CONSUME': 'OUT', 'ADJUST': 'ADJUST'}
                    global_type = type_map.get(trans_type, 'ADJUST')
                    
                    quantity = float(request.POST.get('quantity', 0))
                    notes = request.POST.get('notes', '')

                    if quantity <= 0:
                        raise ValueError("Quantity must be greater than zero.")

                    item = InventoryItem.objects.select_for_update().get(id=item_id)
                    
                    if global_type == 'IN':
                        batch, _ = InventoryBatch.objects.get_or_create(
                            item=item,
                            batch_number=f"STOCK-IN-{timezone.now().strftime('%Y%m%d')}",
                            defaults={'quantity': 0}
                        )
                        batch.quantity += quantity
                        batch.save()
                        item.total_stock += quantity
                    elif global_type == 'OUT':
                        if item.total_stock < quantity:
                            raise ValueError(f"Not enough stock to consume {quantity} {item.unit}.")
                        
                        remaining = quantity
                        batches = item.batches.filter(quantity__gt=0).order_by('expiry_date', 'created_at')
                        for b in batches:
                            if remaining <= 0: break
                            deduct = min(b.quantity, remaining)
                            b.quantity -= deduct
                            b.save()
                            remaining -= deduct
                        item.total_stock -= quantity
                    elif global_type == 'ADJUST':
                        diff = quantity - float(item.total_stock)
                        batch = item.batches.order_by('-created_at').first()
                        if not batch:
                             batch = InventoryBatch.objects.create(item=item, batch_number="ADJUST", quantity=0)
                        batch.quantity += diff
                        batch.save()
                        item.total_stock = quantity
                        quantity = abs(diff)
                    
                    item.save()

                    StockTransaction.objects.create(
                        item=item,
                        transaction_type=global_type,
                        quantity=quantity,
                        performed_by=request.user,
                        notes=notes
                    )
                    return redirect('/categories/labs/inventory/?success=Stock updated successfully.')
                    
                return redirect('/categories/labs/inventory/?error=Unknown action.')
        except Exception as e:
            return redirect(f'/categories/labs/inventory/?error={str(e)}')

class LabStaffManagementView(View):
    """View to track lab staff productivity and profiles."""
    template_name = "categories/labs_staff.html"

    def get(self, request):
        if not request.user.is_authenticated or (
            not request.user.is_superuser
            and not request.user.has_permission('clinics.manage')
        ):
            return redirect('/dashboard/?error=Unauthorized access')

        # Get all users who have been assigned as technicians
        # or users with lab permissions
        User = get_user_model()
        
        # Filter for users who are likely lab staff
        # For simplicity, we'll look at users assigned to lab orders
        # or just all staff users if filtering is needed.
        staff_users = User.objects.filter(
            Q(assigned_lab_orders__isnull=False) | Q(is_staff=True)
        ).distinct()

        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        staff_data = []
        for user in staff_users:
            # 1. Monthly productivity
            monthly_completed = LabOrder.objects.filter(
                technician=user,
                status__in=['COMPLETED', 'REPORT_UPLOADED', 'VERIFIED'],
                updated_at__gte=month_start
            ).count()

            # 2. Total lifetime completed
            total_completed = LabOrder.objects.filter(
                technician=user,
                status__in=['COMPLETED', 'REPORT_UPLOADED', 'VERIFIED']
            ).count()

            # 3. Currently assigned (active)
            active_assignments = LabOrder.objects.filter(
                technician=user,
                status__in=['PENDING', 'COLLECTED', 'PROCESSING']
            ).count()

            staff_data.append({
                'user': user,
                'monthly_completed': monthly_completed,
                'total_completed': total_completed,
                'active_assignments': active_assignments,
            })

        # Sort by monthly productivity
        staff_data.sort(key=lambda x: x['monthly_completed'], reverse=True)
        
        # Calculate summary and percentages
        total_active_workload = sum(item['active_assignments'] for item in staff_data)
        max_monthly = staff_data[0]['monthly_completed'] if staff_data else 0
        
        for item in staff_data:
            if max_monthly > 0:
                item['efficiency_perc'] = round((item['monthly_completed'] / max_monthly) * 100)
            else:
                item['efficiency_perc'] = 0

        return render(request, self.template_name, {
            "staff_data": staff_data,
            "total_active_workload": total_active_workload,
            "now": now,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        })

