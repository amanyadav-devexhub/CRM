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

logger = logging.getLogger(__name__)
User = get_user_model()


class OnboardingStep1View(View):
    """Step 1: Organization details."""
    template_name = "onboarding/step1_org.html"

    def get(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")
        # Pre-fill from session if returning
        data = request.session.get("onboarding_org", {})
        return render(request, self.template_name, {"data": data})

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        org_name = request.POST.get("org_name", "").strip()
        category = request.POST.get("category", "CLINIC")
        org_email = request.POST.get("org_email", "").strip()
        org_phone = request.POST.get("org_phone", "").strip()

        errors = []
        if not org_name:
            errors.append("Organization name is required.")
        if not org_email:
            errors.append("Organization email is required.")

        # Check subdomain availability
        subdomain = slugify(org_name)
        if not subdomain:
            errors.append("Organization name must contain valid characters.")
        elif Tenant.objects.filter(subdomain=subdomain).exists():
            errors.append(f"Subdomain '{subdomain}' is already taken. Try a different name.")

        if errors:
            return render(request, self.template_name, {
                "errors": errors,
                "data": {
                    "org_name": org_name, "category": category,
                    "org_email": org_email, "org_phone": org_phone,
                },
            })

        # Save to session
        request.session["onboarding_org"] = {
            "org_name": org_name,
            "category": category,
            "org_email": org_email,
            "org_phone": org_phone,
            "subdomain": subdomain,
        }

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
            "plan_name": plan.get_name_display(),
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
            # 1. Create Tenant record
            tenant = Tenant.objects.create(
                name=org_data["org_name"],
                category=org_data["category"],
                subdomain=org_data["subdomain"],
                email=org_data["org_email"],
                phone=org_data.get("org_phone", ""),
            )

            # 2. Create Client (schema-per-tenant)
            trial_end = timezone.now() + timedelta(days=14)
            client = Client.objects.create(
                name=org_data["org_name"],
                schema_name=org_data["subdomain"],
                paid_until=trial_end.date(),
                on_trial=True,
            )

            # 3. Create Domain
            Domain.objects.create(
                domain=f"{org_data['subdomain']}.localhost",
                tenant=client,
                is_primary=True,
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

            # 5. Assign user to tenant
            user = request.user
            user.tenant = tenant
            user.save(update_fields=["tenant"])

            # 6. Clean up session
            for key in ["onboarding_org", "onboarding_plan"]:
                request.session.pop(key, None)

            # 7. Redirect to dashboard (same host for now)
            return redirect("/dashboard/")

        except Exception as e:
            logger.error(f"Onboarding failed: {e}")
            return render(request, self.template_name, {
                "org": org_data,
                "plan": plan_data,
                "errors": [f"Something went wrong: {e}"],
            })
