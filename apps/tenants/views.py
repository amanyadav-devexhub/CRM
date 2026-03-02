# apps/tenants/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from django.views import View

from .serializers import TenantCreateSerializer
from .models import Client, Domain, Tenant, SubscriptionPlan, TenantSubscription, Feature, ClinicSettings, TenantFeature

User = get_user_model()


class TenantCreateAPIView(APIView):
    """
    Create a tenant using data passed through the API.
    """
    def post(self, request):
        serializer = TenantCreateSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data

            # 1️⃣ Create Tenant
            tenant = Client.objects.create(
                name=data['name'],
                schema_name=data['schema_name'],
                paid_until="2099-12-31",  # optional
                on_trial=True
            )

            # 2️⃣ Create Domain
            Domain.objects.create(
                domain=data['domain_url'],
                tenant=tenant,
                is_primary=True
            )

            # 3️⃣ Create Superuser in tenant schema — auto-generate username from email
            with schema_context(tenant.schema_name):
                owner_username = data['owner_email'].split('@')[0]
                base_username = owner_username
                counter = 1
                while User.objects.filter(username=owner_username).exists():
                    owner_username = f"{base_username}{counter}"
                    counter += 1

                User.objects.create_superuser(
                    username=owner_username,
                    email=data['owner_email'],
                    password=data['owner_password']
                )

            return Response({
                "message": "Tenant created successfully!",
                "schema_name": tenant.schema_name,
                "domain_url": data['domain_url'],
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# Admin Dashboard — Platform Owner View
# ──────────────────────────────────────────────
class AdminDashboardView(View):
    """
    Platform admin dashboard: tenants, subscriptions, feature flags,
    and global platform-level stats.
    """
    template_name = "dashboard/admin_dashboard.html"

    def get(self, request):
        # Patient stats (platform-wide)
        try:
            from apps.patients.models import Patient
            patient_count = Patient.objects.count()
        except Exception:
            patient_count = 0

        # Tenant stats
        try:
            all_tenants = Tenant.objects.all()
            tenant_count = all_tenants.count()
            active_tenant_count = Tenant.objects.filter(is_active=True).count()
            inactive_tenant_count = tenant_count - active_tenant_count
        except Exception:
            all_tenants = []
            tenant_count = 0
            active_tenant_count = 0
            inactive_tenant_count = 0

        # Subscription stats
        try:
            subscription_count = TenantSubscription.objects.filter(
                status="ACTIVE"
            ).count()
            trial_count = TenantSubscription.objects.filter(
                status="TRIAL"
            ).count()
        except Exception:
            subscription_count = 0
            trial_count = 0

        # Subscription plans
        try:
            plans = SubscriptionPlan.objects.all()
        except Exception:
            plans = []

        # Feature flags (Recent 5 with category counts)
        try:
            recent_features = Feature.objects.all().order_by("-created_at")[:5]
            feature_count = Feature.objects.count()
            
            categories = dict(Tenant.CATEGORY_CHOICES).keys()
            feature_data = []
            
            for f in recent_features:
                category_counts = {}
                for cat in categories:
                    count = TenantFeature.objects.filter(
                        feature_name=f.code,
                        is_enabled=True,
                        tenant__category=cat
                    ).count()
                    if count > 0:
                        category_counts[cat] = count
                feature_data.append({
                    "feature": f,
                    "category_counts": category_counts
                })
            
        except Exception:
            feature_data = []
            feature_count = 0

        # Category totals
        try:
            categories = {
                'CLINIC': all_tenants.filter(category='CLINIC').count(),
                'PHARMACY': all_tenants.filter(category='PHARMACY').count(),
                'HOSPITAL': all_tenants.filter(category='HOSPITAL').count(),
                'LAB': all_tenants.filter(category='LAB').count(),
            }
            tenants = all_tenants.order_by('-created_at')[:5]
        except Exception:
            categories = {'CLINIC': 0, 'PHARMACY': 0, 'HOSPITAL': 0, 'LAB': 0}
            tenants = all_tenants[:5] if hasattr(all_tenants, '__getitem__') else []

        context = {
            "patient_count": patient_count,
            "tenant_count": tenant_count,
            "active_tenant_count": active_tenant_count,
            "inactive_tenant_count": inactive_tenant_count,
            "tenants": tenants,
            "subscription_count": subscription_count,
            "trial_count": trial_count,
            "plans": plans,
            "feature_data": feature_data,
            "feature_count": feature_count,
            "categories": categories,
        }
        return render(request, self.template_name, context)


# ──────────────────────────────────────────────
# Sub-Admin Dashboard — Tenant / Clinic View
# ──────────────────────────────────────────────
class SubAdminDashboardView(View):
    """
    Tenant-level dashboard: renders category-specific dashboard
    (clinic, pharmacy, lab, hospital) based on user's tenant category.
    """

    CATEGORY_TEMPLATES = {
        "CLINIC": "dashboard/index.html",
        "PHARMACY": "dashboard/pharmacy_dashboard.html",
        "LAB": "dashboard/lab_dashboard.html",
        "HOSPITAL": "dashboard/index.html",  # fallback until hospital dashboard exists
    }

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        tenant_category = tenant.category if tenant else "CLINIC"

        template = self.CATEGORY_TEMPLATES.get(tenant_category, "dashboard/index.html")

        # Build context based on category
        if tenant_category == "PHARMACY":
            context = self._pharmacy_context(tenant)
        elif tenant_category == "LAB":
            context = self._lab_context(tenant)
        else:
            context = self._clinic_context(tenant)

        return render(request, template, context)

    def _clinic_context(self, tenant):
        """Clinic / Hospital dashboard context."""
        try:
            from apps.patients.models import Patient
            patient_count = Patient.objects.count()
            recent_patients = Patient.objects.order_by("-created_at")[:10]
        except Exception:
            patient_count = 0
            recent_patients = []

        show_lab_widget = tenant.has_feature("lab") if tenant else False
        show_pharmacy_widget = tenant.has_feature("pharmacy") if tenant else False
        show_ai_widget = tenant.has_feature("ai_notes") if tenant else False
        show_analytics_widget = tenant.has_feature("analytics") if tenant else False

        return {
            "patient_count": patient_count,
            "recent_patients": recent_patients,
            "today_appointments": 0,
            "pending_labs": 0,
            "monthly_revenue": 0,
            "tenant_category": tenant.category if tenant else "CLINIC",
            "show_lab_widget": show_lab_widget,
            "show_pharmacy_widget": show_pharmacy_widget,
            "show_ai_widget": show_ai_widget,
            "show_analytics_widget": show_analytics_widget,
        }

    def _pharmacy_context(self, tenant):
        """Pharmacy dashboard context."""
        from django.utils import timezone as tz
        from django.db.models import Sum

        try:
            from apps.pharmacy.models import Medicine, Sale
            today = tz.now().date()
            thirty_days = today + tz.timedelta(days=30)

            medicines = Medicine.objects.all()
            total_skus = medicines.count()
            low_stock_count = medicines.filter(status='LOW_STOCK').count()
            expired_count = medicines.filter(status='EXPIRED').count()
            expiring_soon_count = medicines.filter(
                expiry_date__lte=thirty_days, expiry_date__gt=today
            ).count()

            today_sales = Sale.objects.filter(
                created_at__date=today
            ).aggregate(total=Sum('grand_total'))['total'] or 0

            inventory_highlights = medicines[:5]
        except Exception:
            total_skus = 0
            low_stock_count = 0
            expired_count = 0
            expiring_soon_count = 0
            today_sales = 0
            inventory_highlights = []

        return {
            "total_skus": total_skus,
            "low_stock_count": low_stock_count,
            "expired_count": expired_count,
            "expiring_soon_count": expiring_soon_count,
            "today_sales": today_sales,
            "inventory_highlights": inventory_highlights,
        }

    def _lab_context(self, tenant):
        """Lab dashboard context."""
        return {
            "pending_tests": 0,
            "samples_received": 0,
            "tat_score": "—",
            "revenue_today": "₹0",
            "test_requests": [],
        }


# ──────────────────────────────────────────────
# Settings — Organization Profile & Preferences
# ──────────────────────────────────────────────
class ClinicSettingsView(View):
    """
    CRUD for ClinicSettings. Displays Basic Info, Localization, Working Hours.
    """
    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        # Attempt to get or create settings
        settings_obj, created = ClinicSettings.objects.get_or_create(tenant=tenant)

        context = {
            "settings": settings_obj,
            "tenant": tenant,
        }
        return render(request, "dashboard/settings.html", context)

    def post(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        settings_obj, created = ClinicSettings.objects.get_or_create(tenant=tenant)

        # 1. Basic Info
        settings_obj.clinic_name = request.POST.get("clinic_name", settings_obj.clinic_name)
        settings_obj.address = request.POST.get("address", settings_obj.address)
        settings_obj.contact_phone = request.POST.get("contact_phone", settings_obj.contact_phone)
        settings_obj.contact_email = request.POST.get("contact_email", settings_obj.contact_email)
        settings_obj.registration_number = request.POST.get("registration_number", settings_obj.registration_number)
        settings_obj.gst_number = request.POST.get("gst_number", settings_obj.gst_number)

        # 2. Localization
        settings_obj.timezone = request.POST.get("timezone", settings_obj.timezone)
        settings_obj.currency = request.POST.get("currency", settings_obj.currency)
        settings_obj.language = request.POST.get("language", settings_obj.language)
        settings_obj.date_format = request.POST.get("date_format", settings_obj.date_format)

        # 3. Working Hours (Construct JSON from form arrays)
        days = request.POST.getlist("day")
        start_times = request.POST.getlist("start_time")
        end_times = request.POST.getlist("end_time")

        working_hours = {}
        for d, st, et in zip(days, start_times, end_times):
            working_hours[d] = {"start": st, "end": et}
        
        settings_obj.working_hours = working_hours
        settings_obj.emergency_available = request.POST.get("emergency_available") == "on"

        settings_obj.save()

        # Update actual tenant name too if clinic name changed
        if "clinic_name" in request.POST:
            tenant.name = request.POST.get("clinic_name")
            tenant.save()

        return redirect("/dashboard/settings/")


class ClinicSettingsView(View):
    """GET/POST clinic settings (org setup, localization, working hours)."""
    template_name = "dashboard/settings.html"

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")
        settings_obj, _ = ClinicSettings.objects.get_or_create(tenant=tenant)
        return render(request, self.template_name, {"settings": settings_obj, "saved": False})

    def post(self, request):
        import json
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")
        settings_obj, _ = ClinicSettings.objects.get_or_create(tenant=tenant)

        # ── Basic Info ──
        settings_obj.clinic_name = request.POST.get("clinic_name", "").strip()
        settings_obj.address = request.POST.get("address", "").strip()
        settings_obj.gst_number = request.POST.get("gst_number", "").strip()
        settings_obj.registration_number = request.POST.get("registration_number", "").strip()
        settings_obj.contact_phone = request.POST.get("contact_phone", "").strip()
        settings_obj.contact_email = request.POST.get("contact_email", "").strip()

        # ── Logo ──
        if "logo" in request.FILES:
            settings_obj.logo = request.FILES["logo"]

        # ── Localization ──
        settings_obj.timezone = request.POST.get("timezone", "Asia/Kolkata")
        settings_obj.currency = request.POST.get("currency", "INR")
        settings_obj.language = request.POST.get("language", "en")
        settings_obj.date_format = request.POST.get("date_format", "DD/MM/YYYY")

        # ── Working Hours (parse JSON from hidden field) ──
        wh_raw = request.POST.get("working_hours", "{}")
        try:
            settings_obj.working_hours = json.loads(wh_raw) if wh_raw else {}
        except json.JSONDecodeError:
            settings_obj.working_hours = {}

        # ── Holidays ──
        holidays_raw = request.POST.get("holidays", "[]")
        try:
            settings_obj.holidays = json.loads(holidays_raw) if holidays_raw else []
        except json.JSONDecodeError:
            settings_obj.holidays = []

        settings_obj.emergency_available = request.POST.get("emergency_available") == "on"

        settings_obj.save()
        return render(request, self.template_name, {"settings": settings_obj, "saved": True})


# ==========================================
# Role-Specific Dashboards (Phase 3 & 4)
# ==========================================

from apps.utils.mixins import HasTenantPermissionMixin

class DoctorDashboardView(HasTenantPermissionMixin, View):
    """Tailored dashboard for doctors."""
    required_permission = "dashboard.doctor"

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        
        context = {
            "tenant_category": tenant.category if tenant else "CLINIC",
            "today_appointments": 0,
            "pending_labs": 0,
        }
        return render(request, "dashboard/roles/doctor.html", context)


class ReceptionDashboardView(HasTenantPermissionMixin, View):
    """Tailored dashboard for receptionists / front desk."""
    required_permission = "dashboard.reception"

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        
        try:
            from apps.patients.models import Patient
            patient_count = Patient.objects.count()
            recent_patients = Patient.objects.order_by("-created_at")[:5]
        except Exception:
            patient_count = 0
            recent_patients = []
            
        context = {
            "tenant_category": tenant.category if tenant else "CLINIC",
            "patient_count": patient_count,
            "recent_patients": recent_patients,
            "today_appointments": 0,
        }
        return render(request, "dashboard/roles/reception.html", context)
