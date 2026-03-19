"""
Onboarding Wizard views.
Multi-step wizard: Org Details → Plan Selection → Review & Submit.
"""
import logging
from django.shortcuts import render, redirect
from django.views import View
from django.db import transaction
from django.utils.text import slugify
from django.utils import timezone
from datetime import timedelta

from apps.tenants.models import (
    Tenant, Client, Domain, SubscriptionPlan, TenantSubscription,
)
from django.contrib.auth import get_user_model

def sanitize_schema_name(subdomain):
    """
    Convert subdomain to valid PostgreSQL schema name.
    Domains allow hyphens, but PostgreSQL schemas do not.
    """
    return subdomain.replace('-', '_')

logger = logging.getLogger(__name__)
User = get_user_model()


class OnboardingStep1View(View):
    """Step 1: Organization details."""
    template_name = "onboarding/step1_org.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")
        from apps.tenants.models import Category
        categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
        # Pre-fill from session if returning
        data = request.session.get("onboarding_org", {})
        return render(request, self.template_name, {"data": data, "categories": categories})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        org_name = request.POST.get("org_name", "").strip()
        category = request.POST.get("category", "CLINIC")

        errors = []
        if not org_name:
            errors.append("Organization name is required.")

        # Check subdomain availability
        subdomain = slugify(org_name)
        if not subdomain:
            errors.append("Organization name must contain valid characters.")
        elif Tenant.objects.filter(subdomain=subdomain).exists():
            errors.append(f"Subdomain '{subdomain}' is already taken. Try a different name.")

        # Collect all dynamic question answers
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
        elif category == "CLINIC":
            setup_answers = {
                "c_type": request.POST.get("c_type", "single"),
                "c_doctors": request.POST.get("c_doctors", "1"),
                "c_specialization": request.POST.get("c_specialization", "general"),
                "c_appointments": "c_appointments" in request.POST,
                "c_walkin": "c_walkin" in request.POST,
                "c_emr": "c_emr" in request.POST,
                "c_insurance": "c_insurance" in request.POST,
                "c_online_pay": "c_online_pay" in request.POST,
                "c_pharmacy": "c_pharmacy" in request.POST,
                "c_lab": "c_lab" in request.POST,
            }
        elif category == "LAB":
            setup_answers = {
                "l_type": request.POST.get("l_type", "diagnostic"),
                "l_inhouse": "l_inhouse" in request.POST,
                "l_home": "l_home" in request.POST,
                "l_hospital_int": "l_hospital_int" in request.POST,
                "l_auto_report": "l_auto_report" in request.POST,
                "l_patient_portal": "l_patient_portal" in request.POST,
                "l_ai_abnormal": "l_ai_abnormal" in request.POST,
                "l_pkg_billing": "l_pkg_billing" in request.POST,
                "l_insurance": "l_insurance" in request.POST,
            }
        elif category == "PHARMACY":
            setup_answers = {
                "p_type": request.POST.get("p_type", "standalone"),
                "p_inventory": "p_inventory" in request.POST,
                "p_expiry": "p_expiry" in request.POST,
                "p_batch": "p_batch" in request.POST,
                "p_gst": "p_gst" in request.POST,
                "p_online_pay": "p_online_pay" in request.POST,
                "p_supplier": "p_supplier" in request.POST,
                "p_rx_int": "p_rx_int" in request.POST,
                "p_auto_deduct": "p_auto_deduct" in request.POST,
            }

        if errors:
            data = {
                "org_name": org_name, "category": category,
                "contact_phone": request.POST.get("contact_phone", "").strip(),
                "contact_email": request.POST.get("contact_email", "").strip(),
                "gst_number": request.POST.get("gst_number", "").strip(),
                "registration_number": request.POST.get("registration_number", "").strip(),
                "address": request.POST.get("address", "").strip(),
                "timezone": request.POST.get("timezone", "Asia/Kolkata"),
                "currency": request.POST.get("currency", "INR"),
                "language": request.POST.get("language", "en"),
                "date_format": request.POST.get("date_format", "DD/MM/YYYY"),
            }
            data.update(setup_answers)
            from apps.tenants.models import Category
            categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
            return render(request, self.template_name, {
                "errors": errors, "data": data, "categories": categories,
            })

        # Save to session — use logged-in user's email as org email
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

        # If the user selected a plan from the landing page, skip step 2
        preselected_plan_id = request.session.get("preselected_plan_id")
        if preselected_plan_id:
            try:
                plan = SubscriptionPlan.objects.get(pk=preselected_plan_id)
                request.session["onboarding_plan"] = {
                    "plan_id": str(plan.pk),
                    "plan_name": plan.display_name or plan.name,
                    "plan_price": str(plan.price),
                }
                # Go directly to confirm step, pop the preselected_plan_id to avoid stale data later
                request.session.pop("preselected_plan_id", None)
                return redirect("/onboarding/confirm/")
            except SubscriptionPlan.DoesNotExist:
                pass

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
        plan_data = request.session.get("onboarding_plan")

        if not org_data or not plan_data:
            return redirect("/onboarding/")

        try:
          with transaction.atomic():
            # 1. Create Client (schema-per-tenant) — auto_create_schema=True
            trial_end = timezone.now() + timedelta(days=14)
            client = Client.objects.create(
            name=org_data["org_name"],
            schema_name=sanitize_schema_name(org_data["subdomain"]), 
            paid_until=trial_end.date(),
            on_trial=True,
            )

            # 2. Create Domain for subdomain routing
            request_host = request.get_host()
            base_host = request_host.split(":")[0]
            # If request_host already has the subdomain (eg test.localhost), extract the root
            parts = base_host.split(".")
            if len(parts) > 1 and parts[0] != "127" and parts[0] != "localhost":
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
            from apps.tenants.models import Category as TenantCategory
            category_obj = TenantCategory.objects.filter(code=org_data["category"]).first()
            tenant = Tenant.objects.create(
                name=org_data["org_name"],
                category=org_data["category"],
                category_obj=category_obj,
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

            # 4b. Features are now derived from the plan directly.
            # TenantFeature records are only created for explicit per-tenant overrides.
                
            # 4c. Auto-provision category-based roles
            from apps.accounts.utils import provision_category_roles
            from apps.accounts.models import Role, Permission
            provision_category_roles(tenant)

            # 5. Assign user to tenant and 'Admin' role (with ALL permissions)
            user = request.user
            user.tenant = tenant
            admin_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Admin",
                defaults={"is_system_role": True},
            )
            # Admin gets every permission
            admin_role.permissions.set(Permission.objects.all())

            user.role = admin_role
            user.save(update_fields=["tenant", "role"])

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
