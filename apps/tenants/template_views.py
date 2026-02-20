# apps/tenants/template_views.py
"""
Template-based views for Tenant management.
"""
from django.shortcuts import render
from django.views import View
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model

from .models import Client, Domain, Tenant

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
        owner_username = data.get("owner_username", "").strip()
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
# Category Panel Views (Frontend-only, planning)
# ──────────────────────────────────────────────
class CategoryIndexView(View):
    """Category selection page showing all healthcare categories."""
    def get(self, request):
        return render(request, "categories/index.html")


class CategoryClinicView(View):
    """Clinic management panel (frontend-only)."""
    def get(self, request):
        return render(request, "categories/clinic.html")


class CategoryPharmacyView(View):
    """Pharmacy management panel (frontend-only)."""
    def get(self, request):
        return render(request, "categories/pharmacy.html")


class CategoryHospitalsView(View):
    """Hospitals management panel (frontend-only)."""
    def get(self, request):
        return render(request, "categories/hospitals.html")


class CategoryLabsView(View):
    """Labs management panel (frontend-only)."""
    def get(self, request):
        return render(request, "categories/labs.html")


class CategoryListView(View):
    """List of tenants filtered by category for Super Admin."""
    template_name = "dashboard/category_list.html"

    def get(self, request, category_slug):
        category_map = {
            'clinic': ('CLINIC', 'Clinics'),
            'pharmacy': ('PHARMACY', 'Pharmacies'),
            'hospitals': ('HOSPITAL', 'Hospitals'),
            'labs': ('LAB', 'Labs'),
        }
        
        if category_slug not in category_map:
            return render(request, "404.html")
            
        category_code, category_display = category_map[category_slug]
        tenants = Tenant.objects.filter(category=category_code).order_by("-created_at")
        
        context = {
            "category_name": category_display,
            "category_slug": category_slug,
            "tenants": tenants,
        }
        return render(request, self.template_name, context)

class PharmacyInventoryView(View):
    """Pharmacy inventory management view."""
    template_name = "categories/pharmacy_inventory.html"
    def get(self, request):
        return render(request, self.template_name)

class PharmacySalesView(View):
    """Pharmacy sales/POS view."""
    template_name = "categories/pharmacy_sales.html"
    def get(self, request):
        return render(request, self.template_name)

class PharmacyPrescriptionsView(View):
    """Pharmacy prescriptions view."""
    template_name = "categories/pharmacy_prescriptions.html"
    def get(self, request):
        return render(request, self.template_name)

