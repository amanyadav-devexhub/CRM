# apps/tenants/template_views.py
"""
Template-based views for Tenant management.
"""
from django.shortcuts import render
from django.views import View
from django_tenants.utils import schema_context
from django.contrib.auth import get_user_model

from .models import Client, Domain

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
