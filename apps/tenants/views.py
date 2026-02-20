# apps/tenants/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model
from django.shortcuts import render
from django.views import View

from .serializers import TenantCreateSerializer
from .models import Client, Domain, Tenant, SubscriptionPlan, TenantSubscription, Feature

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

            # 3️⃣ Create Superuser in tenant schema using API-provided data
            with schema_context(tenant.schema_name):
                if User.objects.filter(username=data['owner_username']).exists():
                    return Response(
                        {"error": "Username already exists in tenant schema"},
                        status=status.HTTP_400_BAD_REQUEST
                    )

                User.objects.create_superuser(
                    username=data['owner_username'],
                    email=data['owner_email'],
                    password=data['owner_password']
                )

            return Response({
                "message": "Tenant created successfully!",
                "schema_name": tenant.schema_name,
                "domain_url": data['domain_url'],
                "admin_username": data['owner_username']
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
            tenants = Tenant.objects.all()
            tenant_count = tenants.count()
            active_tenant_count = Tenant.objects.filter(is_active=True).count()
            inactive_tenant_count = tenant_count - active_tenant_count
        except Exception:
            tenants = []
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

        # Feature flags
        try:
            features = Feature.objects.all()
            feature_count = features.count()
        except Exception:
            features = []
            feature_count = 0

        # Category totals
        try:
            categories = {
                'CLINIC': tenants.filter(category='CLINIC').count(),
                'PHARMACY': tenants.filter(category='PHARMACY').count(),
                'HOSPITAL': tenants.filter(category='HOSPITAL').count(),
                'LAB': tenants.filter(category='LAB').count(),
            }
        except Exception:
            categories = {'CLINIC': 0, 'PHARMACY': 0, 'HOSPITAL': 0, 'LAB': 0}

        context = {
            "patient_count": patient_count,
            "tenant_count": tenant_count,
            "active_tenant_count": active_tenant_count,
            "inactive_tenant_count": inactive_tenant_count,
            "tenants": tenants,
            "subscription_count": subscription_count,
            "trial_count": trial_count,
            "plans": plans,
            "features": features,
            "feature_count": feature_count,
            "categories": categories,
        }
        return render(request, self.template_name, context)


# ──────────────────────────────────────────────
# Sub-Admin Dashboard — Tenant / Clinic View
# ──────────────────────────────────────────────
class SubAdminDashboardView(View):
    """
    Tenant-level dashboard: patients, appointments, labs, revenue
    for the hospital/clinic/pharmacy.
    """
    template_name = "dashboard/index.html"

    def get(self, request):
        # Patient stats (tenant-level)
        try:
            from apps.patients.models import Patient
            patient_count = Patient.objects.count()
            recent_patients = Patient.objects.order_by("-created_at")[:10]
        except Exception:
            patient_count = 0
            recent_patients = []

        # Appointments today (placeholder — appointments app not built yet)
        today_appointments = 0

        # Pending lab results (placeholder — labs app not built yet)
        pending_labs = 0

        # Monthly revenue (placeholder — billing app not built yet)
        monthly_revenue = 0

        # Get tenant category (mock logic for now since we're in template_views context)
        # In a real scenario, this would come from the current tenant object
        tenant_category = "CLINIC"  # Default fallback
        
        context = {
            "patient_count": patient_count,
            "recent_patients": recent_patients,
            "today_appointments": today_appointments,
            "pending_labs": pending_labs,
            "monthly_revenue": monthly_revenue,
            "tenant_category": tenant_category,
        }
        return render(request, self.template_name, context)
