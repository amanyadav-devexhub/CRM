# apps/tenants/template_views.py
"""
Template-based views for Tenant management and Category hubs.
"""
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.views import View
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from django.db.models import Sum, Count

from .models import Client, Domain, Tenant, Category

User = get_user_model()


class TenantCreatePageView(View):
    """Render the tenant creation form and process submissions."""

    def get(self, request):
        return render(request, "tenants/tenant_create.html")

    def post(self, request):
        data = request.POST
        name = data.get("name", "").strip()
        schema_name = data.get("schema_name", "").strip()
        domain_url = data.get("domain_url", "").strip()
        owner_email = data.get("owner_email", "").strip()
        owner_password = data.get("owner_password", "")

        # Validation
        if Client.objects.filter(schema_name=schema_name).exists():
            return render(request, "tenants/tenant_create.html", {
                "form_errors": "Schema name already exists.",
            })
        if Domain.objects.filter(domain=domain_url).exists():
            return render(request, "tenants/tenant_create.html", {
                "form_errors": "Domain URL already exists.",
            })

        # Auto-generate username from email
        owner_username = owner_email.split("@")[0]
        base_username = owner_username
        counter = 1

        try:
            tenant = Client.objects.create(
                name=name,
                schema_name=schema_name,
                paid_until="2099-12-31",
                on_trial=True,
            )
            Domain.objects.create(
                domain=domain_url,
                tenant=tenant,
                is_primary=True,
            )
            with schema_context(tenant.schema_name):
                while User.objects.filter(username=owner_username).exists():
                    owner_username = f"{base_username}{counter}"
                    counter += 1
                User.objects.create_superuser(
                    username=owner_username,
                    email=owner_email,
                    password=owner_password,
                )
            return render(request, "tenants/tenant_create.html", {
                "success_message": f"Tenant '{name}' created successfully! Schema: {schema_name}, Domain: {domain_url}",
            })
        except Exception as e:
            return render(request, "tenants/tenant_create.html", {
                "form_errors": str(e),
            })


# ──────────────────────────────────────────────
# Category Index — dynamic CRUD
# ──────────────────────────────────────────────
class CategoryIndexView(View):
    """Category management page with full CRUD operations."""

    def get(self, request):
        from django.contrib import messages as msg_framework

        q = request.GET.get("q", "").strip()
        categories = Category.objects.all()

        if q:
            categories = categories.filter(name__icontains=q) | categories.filter(code__icontains=q)

        cat_data = []
        for cat in categories:
            from django.db.models import Q
            tenant_count = Tenant.objects.filter(
                Q(category=cat.code) | Q(category_obj=cat)
            ).distinct().count()
            cat_data.append({
                "category": cat,
                "tenant_count": tenant_count,
            })

        # Editing support
        edit_id = request.GET.get("edit")
        editing = None
        if edit_id:
            try:
                editing = Category.objects.get(pk=edit_id)
            except Category.DoesNotExist:
                pass

        # Build choices with selected flags for the template
        icon_choices = [
            {"value": val, "label": label, "selected": editing and editing.icon == val}
            for val, label in Category.ICON_CHOICES
        ]
        color_choices = [
            {"value": val, "label": label, "selected": editing and editing.color == val}
            for val, label in Category.COLOR_CHOICES
        ]

        context = {
            "cat_data": cat_data,
            "total": len(cat_data),
            "search_query": q,
            "editing": editing,
            "icon_choices": icon_choices,
            "color_choices": color_choices,
        }
        return render(request, "categories/index.html", context)

    def post(self, request):
        from django.contrib import messages

        action = request.POST.get("action")

        if action == "create":
            code = request.POST.get("code", "").strip().upper()
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            icon = request.POST.get("icon", "category")
            color = request.POST.get("color", "blue")
            sort_order = request.POST.get("sort_order", "0")

            if not code or not name:
                messages.error(request, "Code and Name are required.")
                return redirect("/categories/")

            if Category.objects.filter(code=code).exists():
                messages.error(request, f"Category with code '{code}' already exists.")
                return redirect("/categories/")

            try:
                Category.objects.create(
                    code=code,
                    name=name,
                    description=description,
                    icon=icon,
                    color=color,
                    sort_order=int(sort_order) if sort_order else 0,
                )
                messages.success(request, f"Category '{name}' created successfully.")
            except Exception as e:
                messages.error(request, f"Error creating category: {e}")

            return redirect("/categories/")

        cat_id = request.POST.get("category_id")
        try:
            cat = Category.objects.get(pk=cat_id)
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
            return redirect("/categories/")

        if action == "update":
            cat.name = request.POST.get("name", cat.name).strip()
            cat.description = request.POST.get("description", cat.description).strip()
            cat.icon = request.POST.get("icon", cat.icon)
            cat.color = request.POST.get("color", cat.color)
            sort_order = request.POST.get("sort_order", str(cat.sort_order))
            cat.sort_order = int(sort_order) if sort_order else cat.sort_order
            cat.save()
            messages.success(request, f"Category '{cat.name}' updated.")

        elif action == "activate":
            cat.is_active = True
            cat.save(update_fields=["is_active"])
            messages.success(request, f"'{cat.name}' activated.")

        elif action == "deactivate":
            cat.is_active = False
            cat.save(update_fields=["is_active"])
            messages.success(request, f"'{cat.name}' deactivated.")

        elif action == "delete":
            from django.db.models import Q
            tenant_count = Tenant.objects.filter(
                Q(category=cat.code) | Q(category_obj=cat)
            ).distinct().count()
            if tenant_count > 0:
                messages.error(request, f"Cannot delete '{cat.name}' — {tenant_count} tenant(s) are using it. Deactivate it instead.")
            else:
                name = cat.name
                cat.delete()
                messages.success(request, f"Category '{name}' deleted permanently.")

        return redirect("/categories/")


# ──────────────────────────────────────────────
# Clinic Hub — real data
# ──────────────────────────────────────────────
class CategoryClinicView(View):
    """Clinic dashboard with real doctor/appointment stats."""
    def get(self, request):
        # Non-superadmin users go to the full dashboard
        if not request.user.is_superuser:
            return redirect("/dashboard/")
        from apps.clinical.models import Doctor
        from apps.appointments.models import Appointment
        from apps.patients.models import Patient

        today = timezone.now().date()

        active_doctors = Doctor.objects.filter(is_active=True).count()
        appointments_today = Appointment.objects.filter(appointment_date=today).count()
        total_patients = Patient.objects.count()

        # Today's revenue from completed appointments
        from django.db.models import Sum
        revenue = Appointment.objects.filter(
            appointment_date=today, status='COMPLETED'
        ).aggregate(total=Sum('fee'))['total'] or 0

        # Upcoming appointments (today, not completed/cancelled)
        upcoming = Appointment.objects.filter(
            appointment_date=today
        ).exclude(status__in=['COMPLETED', 'CANCELLED']).select_related('doctor')[:10]

        context = {
            "active_doctors": active_doctors,
            "appointments_today": appointments_today,
            "total_patients": total_patients,
            "revenue_today": f"₹{revenue:,.0f}",
            "upcoming_appointments": upcoming,
        }
        return render(request, "categories/clinic.html", context)


class ClinicDashboardAPIView(View):
    """JSON API for real-time clinic dashboard stats (polled via AJAX)."""
    def get(self, request):
        from apps.clinical.models import Doctor
        from apps.appointments.models import Appointment
        from apps.patients.models import Patient
        from django.http import JsonResponse
        from django.db.models import Sum

        today = timezone.now().date()

        active_doctors = Doctor.objects.filter(is_active=True).count()
        appointments_today = Appointment.objects.filter(appointment_date=today).count()
        total_patients = Patient.objects.count()

        revenue = Appointment.objects.filter(
            appointment_date=today, status='COMPLETED'
        ).aggregate(total=Sum('fee'))['total'] or 0

        # Upcoming appointments
        upcoming = Appointment.objects.filter(
            appointment_date=today
        ).exclude(status__in=['COMPLETED', 'CANCELLED']).select_related('doctor')[:10]

        STATUS_BADGES = {
            'CONFIRMED': {'label': 'Confirmed', 'class': 'active'},
            'SCHEDULED': {'label': 'Scheduled', 'class': 'trial'},
            'IN_PROGRESS': {'label': 'In Progress', 'class': 'in-progress'},
        }

        appointments_list = []
        for a in upcoming:
            badge = STATUS_BADGES.get(a.status, {'label': a.get_status_display(), 'class': ''})
            appointments_list.append({
                'time': a.appointment_time.strftime('%I:%M %p'),
                'patient': a.patient_name,
                'doctor': f'Dr. {a.doctor.name}',
                'status': a.status,
                'status_label': badge['label'],
                'status_class': badge['class'],
            })

        return JsonResponse({
            'active_doctors': active_doctors,
            'appointments_today': appointments_today,
            'total_patients': total_patients,
            'revenue_today': f'₹{revenue:,.0f}',
            'upcoming_appointments': appointments_list,
            'timestamp': timezone.now().strftime('%I:%M:%S %p'),
        })


class ClinicDoctorsView(View):
    """Clinic doctors management with add/list functionality."""
    template_name = "categories/clinic_doctors.html"

    def get(self, request):
        from apps.clinical.models import Doctor
        doctors = Doctor.objects.all()
        context = {
            "doctors": doctors,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.clinical.models import Doctor
        from django.shortcuts import redirect

        print("=" * 60)
        print("📥 POST received on clinic-doctors")
        print(f"   POST data: {dict(request.POST)}")
        print("=" * 60)

        name = request.POST.get('name', '').strip()
        specialization = request.POST.get('specialization', 'General')
        phone = request.POST.get('phone', '').strip()
        email = request.POST.get('email', '').strip()
        qualification = request.POST.get('qualification', '').strip()

        try:
            doc = Doctor.objects.create(
                name=name,
                specialization=specialization,
                phone=phone,
                email=email,
                qualification=qualification,
            )
            print(f"✅ Doctor created: {doc.name} (ID: {doc.id})")
            msg = f"Successfully added Dr. {name}"
            return redirect(f"{request.path}?success={msg}")
        except Exception as e:
            print(f"❌ Error creating doctor: {e}")
            import traceback
            traceback.print_exc()
            doctors = Doctor.objects.all()
            return render(request, self.template_name, {
                "doctors": doctors,
                "error_message": str(e),
            })


class ClinicAppointmentsView(View):
    """Clinic appointment management with add/list functionality."""
    template_name = "categories/clinic_appointments.html"

    def get(self, request):
        from apps.appointments.models import Appointment
        from apps.clinical.models import Doctor

        appointments = Appointment.objects.select_related('doctor').all()
        doctors = Doctor.objects.filter(is_active=True)
        context = {
            "appointments": appointments,
            "doctors": doctors,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.appointments.models import Appointment
        from apps.clinical.models import Doctor
        from django.shortcuts import redirect
        from datetime import datetime as _dt

        print("=" * 60)
        print("📥 POST received on clinic-appointments")
        print(f"   POST data: {dict(request.POST)}")
        print("=" * 60)

        patient_name = request.POST.get('patient_name', '').strip()
        doctor_id = request.POST.get('doctor', '')
        date_str = request.POST.get('appointment_date', '')
        time_str = request.POST.get('appointment_time', '')
        fee = request.POST.get('fee', '0')
        notes = request.POST.get('notes', '').strip()

        try:
            fee = float(fee)
        except (ValueError, TypeError):
            fee = 0.0

        try:
            doctor = Doctor.objects.get(id=doctor_id)
            appt_date = _dt.strptime(date_str, "%Y-%m-%d").date() if date_str else timezone.now().date()
            appt_time = _dt.strptime(time_str, "%H:%M").time() if time_str else timezone.now().time()

            appt = Appointment.objects.create(
                patient_name=patient_name,
                doctor=doctor,
                appointment_date=appt_date,
                appointment_time=appt_time,
                fee=fee,
                notes=notes,
            )
            print(f"✅ Appointment created: {appt}")
            msg = f"Appointment booked for {patient_name} with Dr. {doctor.name}"
            return redirect(f"{request.path}?success={msg}")
        except Exception as e:
            print(f"❌ Error creating appointment: {e}")
            import traceback
            traceback.print_exc()
            appointments = Appointment.objects.select_related('doctor').all()
            doctors = Doctor.objects.filter(is_active=True)
            return render(request, self.template_name, {
                "appointments": appointments,
                "doctors": doctors,
                "error_message": str(e),
            })


class ClinicPatientsView(View):
    """List patients for the clinic hub with search/filter and add-patient."""
    template_name = "categories/clinic_patients.html"

    BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    def get(self, request):
        from apps.patients.models import Patient
        from django.db.models import Q

        patients = Patient.objects.all()

        search = request.GET.get('search', '').strip()
        gender = request.GET.get('gender', '').strip()
        blood = request.GET.get('blood_group', '').strip()

        if search:
            patients = patients.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(patient_id__icontains=search)
                | Q(email__icontains=search)
            )
        if gender:
            patients = patients.filter(gender=gender)
        if blood:
            patients = patients.filter(blood_group=blood)

        context = {
            "patients": patients,
            "blood_groups": self.BLOOD_GROUPS,
            "search_query": search,
            "gender_filter": gender,
            "blood_filter": blood,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.patients.models import Patient
        from django.shortcuts import redirect

        print("=" * 60)
        print("📥 POST received on clinic-patients")
        print(f"   POST data: {dict(request.POST)}")
        print("=" * 60)

        try:
            patient = Patient.objects.create(
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                date_of_birth=request.POST.get('date_of_birth') or None,
                gender=request.POST.get('gender', ''),
                blood_group=request.POST.get('blood_group', ''),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                notes=request.POST.get('notes', '').strip(),
            )
            print(f"✅ Patient created: {patient.full_name} (ID: {patient.patient_id})")
            msg = f"Successfully registered {patient.full_name} ({patient.patient_id})"
            return redirect(f"{request.path}?success={msg}")
        except Exception as e:
            print(f"❌ Error creating patient: {e}")
            import traceback
            traceback.print_exc()
            from apps.patients.models import Patient as P
            patients = P.objects.all()
            return render(request, self.template_name, {
                "patients": patients,
                "blood_groups": self.BLOOD_GROUPS,
                "error_message": str(e),
            })


# ──────────────────────────────────────────────
# Pharmacy Hub — real data
# ──────────────────────────────────────────────
class CategoryPharmacyView(View):
    """Pharmacy dashboard with real inventory stats."""
    def get(self, request):

        from apps.pharmacy.models import Medicine, Sale

        today = timezone.now().date()
        thirty_days = today + timezone.timedelta(days=30)

        medicines = Medicine.objects.all()
        total_skus = medicines.count()
        low_stock_count = medicines.filter(status='LOW_STOCK').count()
        expired_count = medicines.filter(status='EXPIRED').count()
        expiring_soon_count = medicines.filter(
            expiry_date__lte=thirty_days,
            expiry_date__gt=today
        ).count()

        # Today's sales
        today_sales = Sale.objects.filter(
            created_at__date=today
        ).aggregate(total=Sum('grand_total'))['total'] or 0

        # Inventory highlights (top 4 medicines)
        inventory_highlights = medicines[:4]

        context = {
            "total_skus": total_skus,
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon_count,
            "today_sales": today_sales,
            "inventory_highlights": inventory_highlights,
        }
        return render(request, "categories/pharmacy.html", context)


# ──────────────────────────────────────────────
# Hospitals Hub (placeholder stats)
# ──────────────────────────────────────────────
class CategoryHospitalsView(View):
    """Hospitals management panel with placeholder stats."""
    def get(self, request):
        context = {
            "bed_occupancy_pct": 0,
            "available_icu": 0,
            "er_load": "—",
            "monthly_admits": 0,
            "departments": [],
        }
        return render(request, "categories/hospitals.html", context)


# ──────────────────────────────────────────────
# Labs Hub (placeholder stats)
# ──────────────────────────────────────────────
class CategoryLabsView(View):
    """Labs management panel with real stats."""
    def get(self, request):

        context = {
            "pending_tests": 0,
            "samples_received": 0,
            "tat_score": "—",
            "revenue_today": "₹0",
            "test_requests": [],
        }
        return render(request, "categories/labs.html", context)


class CategoryLabsTestCatalogView(View):
    """Placeholder view for Lab Test Catalog."""
    def get(self, request):
        return render(request, "categories/labs.html", {
            "pending_tests": 0,
            "samples_received": 0,
            "tat_score": "—",
            "revenue_today": "₹0",
            "test_requests": [],
            "alert": "Test Catalog is under construction",
        })


class CategoryLabsOrderListView(View):
    """Placeholder view for Lab Orders List."""
    def get(self, request):
        return render(request, "categories/labs.html", {
            "pending_tests": 0,
            "samples_received": 0,
            "tat_score": "—",
            "revenue_today": "₹0",
            "test_requests": [],
            "alert": "Order list is under construction",
        })


# ──────────────────────────────────────────────
# Category List — tenants filtered by category
# ──────────────────────────────────────────────
class CategoryListView(View):
    """List of tenants filtered by category for Super Admin."""
    template_name = "dashboard/category_list.html"

    def get(self, request, category_slug):
        # Dynamic lookup from Category model
        cat = Category.objects.filter(code__iexact=category_slug).first()

        if not cat:
            return render(request, "dashboard/category_list.html", {
                "category_name": "Unknown",
                "tenants": [],
            })

        from django.db.models import Q
        tenants_query = Tenant.objects.filter(
            Q(category=cat.code) | Q(category_obj=cat)
        ).distinct().order_by("-created_at")
        
        # Pagination setup (10 tenants per page)
        paginator = Paginator(tenants_query, 10)
        page_number = request.GET.get('page', 1)
        tenants = paginator.get_page(page_number)

        context = {
            "category_name": cat.name,
            "category_slug": category_slug,
            "tenants": tenants,
            "tenant_count": tenants_query.count(),
        }
        return render(request, self.template_name, context)


# ──────────────────────────────────────────────
# Pharmacy Sub-views — real data
# ──────────────────────────────────────────────
class PharmacyInventoryView(View):
    """Pharmacy inventory management with real Medicine data."""
    template_name = "categories/pharmacy_inventory.html"

    def get(self, request):
        from apps.pharmacy.models import Medicine
        medicines = Medicine.objects.all()

        # Optional filter from query param
        filter_type = request.GET.get('filter')
        if filter_type == 'low-stock':
            medicines = medicines.filter(status__in=['LOW_STOCK', 'EXPIRED'])

        context = {
            "medicines": medicines,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        """Handle Add Stock form submission."""
        from apps.pharmacy.models import Medicine
        from django.shortcuts import redirect
        from urllib.parse import urlencode
        import uuid as _uuid

        print("=" * 60)
        print("📥 POST received on pharmacy-inventory")
        print(f"   POST data: {dict(request.POST)}")
        print("=" * 60)

        name = request.POST.get('name', '').strip()
        batch = request.POST.get('batch_number', '').strip()
        qty = request.POST.get('quantity', '0')
        price = request.POST.get('price', '0')
        category = request.POST.get('category', 'General')
        expiry = request.POST.get('expiry_date', '')

        try:
            qty = int(qty)
            price = float(price)
        except (ValueError, TypeError):
            qty = 0
            price = 0.0

        if not expiry:
            expiry = (timezone.now() + timezone.timedelta(days=365)).date()
        else:
            from datetime import datetime as _dt
            expiry = _dt.strptime(expiry, "%Y-%m-%d").date()

        # Auto-generate SKU
        sku = f"PHA-{_uuid.uuid4().hex[:6].upper()}"

        try:
            med = Medicine.objects.create(
                name=name,
                sku=sku,
                category=category,
                batch_number=batch,
                price=price,
                stock=qty,
                expiry_date=expiry,
            )
            print(f"✅ Medicine created: {med.name} (SKU: {med.sku}, ID: {med.id})")
            msg = f"Successfully added {name} (Batch {batch})"
            return redirect(f"{request.path}?success={msg}")
        except Exception as e:
            print(f"❌ Error creating medicine: {e}")
            import traceback
            traceback.print_exc()
            medicines = Medicine.objects.all()
            return render(request, self.template_name, {
                "medicines": medicines,
                "error_message": str(e),
            })


class PharmacySalesView(View):
    """Pharmacy sales/POS view with real sale data."""
    template_name = "categories/pharmacy_sales.html"

    def get(self, request):
        from apps.pharmacy.models import Sale
        recent_sales = Sale.objects.all()[:10]
        context = {
            "recent_sales": recent_sales,
        }
        return render(request, self.template_name, context)


class PharmacyPrescriptionsView(View):
    """Pharmacy prescriptions view with real data."""
    template_name = "categories/pharmacy_prescriptions.html"

    def get(self, request):
        from apps.pharmacy.models import Prescription
        prescriptions = Prescription.objects.all()
        context = {
            "prescriptions": prescriptions,
        }
        return render(request, self.template_name, context)
