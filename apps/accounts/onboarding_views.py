"""
Onboarding Wizard views.
Multi-step wizard: Org Details → Plan Selection → Review & Submit.
"""
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import (
    Tenant, Client, Domain, SubscriptionPlan, TenantSubscription,
)
from django.contrib.auth import get_user_model
from django.db import connection

logger = logging.getLogger(__name__)
User = get_user_model()

class OnboardingStep1View(View):
    """Step 1: Organization details."""
    template_name = "onboarding/step1_org.html"

    def get(self, request):
        print("\n===== STEP 1 GET DEBUG =====")
        print("Schema:", connection.schema_name)
        print("Session key:", request.session.session_key)
        print("Existing session data:", request.session.get("onboarding_org"))
        print("============================\n")

        if not request.user.is_authenticated:
            return redirect("/login/")

        data = request.session.get("onboarding_org", {})
        return render(request, self.template_name, {"data": data})

    def post(self, request):
        print("\n===== STEP 1 POST DEBUG =====")
        print("Schema:", connection.schema_name)
        print("Session key (before save):", request.session.session_key)
        print("User:", request.user)
        print("POST category RAW:", request.POST.get("category"))
        print("============================\n")

        if not request.user.is_authenticated:
            return redirect("/login/")

        org_name = request.POST.get("org_name", "").strip()
        category = request.POST.get("category", "CLINIC")

        print("Normalized category:", category)

        errors = []
        if not org_name:
            errors.append("Organization name is required.")

        subdomain = slugify(org_name)

        # Collect dynamic answers
        setup_answers = {}
        if category == "HOSPITAL":
            setup_answers = {
                "h_branches": request.POST.get("h_branches", "1"),
                "h_doctors": request.POST.get("h_doctors", "10"),
                "h_departments": request.POST.get("h_departments", "5"),
                "h_icu": "h_icu" in request.POST,
                "h_ipd": "h_ipd" in request.POST,
                "h_emr": "h_emr" in request.POST,
                "h_ot": "h_ot" in request.POST,
                "h_beds": "h_beds" in request.POST,
                "h_lab": "h_lab" in request.POST,
                "h_pharmacy": "h_pharmacy" in request.POST,
                "h_insurance": "h_insurance" in request.POST,
                "h_multi_billing": "h_multi_billing" in request.POST,
                "h_pkg_billing": "h_pkg_billing" in request.POST,
                "h_ai_notes": "h_ai_notes" in request.POST,
                "h_ai_risk": "h_ai_risk" in request.POST,
                "h_volume": request.POST.get("h_volume", "500"),
            }

        print("Setup answers collected:", setup_answers)

        # Save to session
        session_data = {
            "org_name": org_name,
            "category": category,
            "org_email": request.POST.get("contact_email", request.user.email).strip(),
            "contact_phone": request.POST.get("contact_phone", "").strip(),
            "gst_number": request.POST.get("gst_number", "").strip(),
            "registration_number": request.POST.get("registration_number", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "timezone": request.POST.get("timezone", "Asia/Kolkata"),
            "currency": request.POST.get("currency", "INR"),
            "language": request.POST.get("language", "en"),
            "date_format": request.POST.get("date_format", "DD/MM/YYYY"),
            "subdomain": subdomain,
            "setup": setup_answers,
        }

        request.session["onboarding_org"] = session_data
        request.session.modified = True  # force save

        print("\nSaved session data:")
        print(request.session["onboarding_org"])
        print("Session key (after save):", request.session.session_key)
        print("=================================\n")

        return redirect("/onboarding/plan/")


class OnboardingStep2View(View):
    """Step 2: Select plan and modules."""
    template_name = "onboarding/step2_plan.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")
        if "onboarding_org" not in request.session:
            return redirect("/onboarding/")

        plans = SubscriptionPlan.objects.all()
        selected = request.session.get("onboarding_plan", {})
        return render(request, self.template_name, {
            "plans": plans,
            "selected": selected,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        plan_id = request.POST.get("plan_id")

        errors = []
        if not plan_id:
            errors.append("Please select a plan.")
            plans = SubscriptionPlan.objects.all()
            return render(request, self.template_name, {
                "errors": errors, "plans": plans, "selected": {},
            })

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            errors.append("Invalid plan selected.")
            plans = SubscriptionPlan.objects.all()
            return render(request, self.template_name, {
                "errors": errors, "plans": plans, "selected": {},
            })

        request.session["onboarding_plan"] = {
            "plan_id": str(plan.pk),
            "plan_name": plan.display_name or plan.name,
            "plan_price": str(plan.price),
        }

        return redirect("/onboarding/confirm/")


class OnboardingStep3View(View):
    """Step 3: Review and confirm — create tenant."""
    template_name = "onboarding/step3_confirm.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        org_data = request.session.get("onboarding_org")
        plan_data = request.session.get("onboarding_plan")

        if not org_data:
            return redirect("/onboarding/")
        if not plan_data:
            return redirect("/onboarding/plan/")

        return render(request, self.template_name, {
            "org": org_data,
            "plan": plan_data,
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        org_data = request.session.get("onboarding_org")
        print(org_data, "=======")
        plan_data = request.session.get("onboarding_plan")

        if not org_data or not plan_data:
            return redirect("/onboarding/")

        try:
            # 1. Create Client (schema-per-tenant) — auto_create_schema=True
            trial_end = timezone.now() + timedelta(days=14)
            client = Client.objects.create(
                name=org_data["org_name"],
                schema_name=org_data["subdomain"],
                paid_until=trial_end.date(),
                on_trial=True,
            )

            # 2. Create Domain for subdomain routing
            request_host = request.get_host()
            base_host = request_host.split(":")[0]
            # If request_host already has the subdomain (eg test.localhost), extract the root
            parts = base_host.split(".")
            if base_host in ("127.0.0.1", "0.0.0.0"):
                root_host = "localhost"
            elif len(parts) > 1 and parts[0] != "localhost":
                root_host = ".".join(parts[1:])
            else:
                root_host = base_host

            tenant_domain = f"{org_data['subdomain']}.{root_host}"
            Domain.objects.create(
                domain=tenant_domain,
                tenant=client,
                is_primary=True,
            )

            # 3. Create Tenant record (app-level) and link to Client
            tenant = Tenant.objects.create(
                name=org_data["org_name"],
                category=org_data["category"],
                subdomain=org_data["subdomain"],
                email=org_data["org_email"],
                phone="",
                client=client,
            )

            # 4. Create subscription
            plan = SubscriptionPlan.objects.get(pk=plan_data["plan_id"])
            TenantSubscription.objects.create(
                tenant=tenant,
                plan=plan,
                status="TRIAL",
                start_date=timezone.now(),
                end_date=trial_end,
                trial=True,
            )

            # 4b. Auto-provision features from plan
            from apps.tenants.models import TenantFeature
            for feature in plan.features.all():
                TenantFeature.objects.get_or_create(
                    tenant=tenant,
                    feature_name=feature.code,
                    defaults={"is_enabled": True},
                )

            # 5. Assign user to tenant
            user = request.user
            user.tenant = tenant
            user.save(update_fields=["tenant"])

            # 6. Seed default data in the new tenant schema
            from django_tenants.utils import schema_context
            from apps.tenants.models import ClinicSettings

            with schema_context(client.schema_name):
                ClinicSettings.objects.create(
                    tenant=tenant,
                    clinic_name=org_data["org_name"],
                    contact_email=org_data.get("org_email", ""),
                    contact_phone=org_data.get("contact_phone", ""),
                    gst_number=org_data.get("gst_number", ""),
                    registration_number=org_data.get("registration_number", ""),
                    address=org_data.get("address", ""),
                    timezone=org_data.get("timezone", "Asia/Kolkata"),
                    currency=org_data.get("currency", "INR"),
                    language=org_data.get("language", "en"),
                    date_format=org_data.get("date_format", "DD/MM/YYYY"),
                    working_hours={
                        "mon": {"open": "09:00", "close": "18:00"},
                        "tue": {"open": "09:00", "close": "18:00"},
                        "wed": {"open": "09:00", "close": "18:00"},
                        "thu": {"open": "09:00", "close": "18:00"},
                        "fri": {"open": "09:00", "close": "18:00"},
                        "sat": {"open": "09:00", "close": "14:00"},
                    },
                )

            # 7. Clean up session
            for key in ["onboarding_org", "onboarding_plan"]:
                request.session.pop(key, None)

            # 8. Redirect to tenant subdomain via auth bridge
            from django.core import signing
            token = signing.dumps({"user_id": user.pk}, salt="auth-bridge")
            scheme = "https" if request.is_secure() else "http"
            port_part = request.get_host().split(":")[1] if ":" in request.get_host() else ""
            port_suffix = f":{port_part}" if port_part else ""
            return redirect(f"{scheme}://{tenant_domain}{port_suffix}/auth-bridge/?token={token}")

        except Exception as e:
            logger.error(f"Onboarding failed: {e}")
            return render(request, self.template_name, {
                "org": org_data,
                "plan": plan_data,
                "errors": [f"Something went wrong: {e}"],
            })
