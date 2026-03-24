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
from apps.core.models import Country, Currency, Language, Timezone, DateFormat
from django.contrib.auth import get_user_model

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
        countries = Country.objects.filter(status=True).order_by('name')
        currencies = Currency.objects.filter(status=True).order_by('code')
        languages = Language.objects.filter(status=True).order_by('name')
        timezones = Timezone.objects.filter(status=True).order_by('name')
        date_formats = DateFormat.objects.filter(status=True).order_by('label')

        # Pre-fill from session if returning
        data = request.session.get("onboarding_org", {})
        return render(request, self.template_name, {
            "data": data,
            "categories": categories,
            "countries": countries,
            "currencies": currencies,
            "languages": languages,
            "timezones": timezones,
            "date_formats": date_formats
        })

    def post(self, request):
        if not request.user.is_authenticated:
            return redirect("/login/")

        org_name = request.POST.get("org_name", "").strip()
        category = request.POST.get("category", "CLINIC")
        country_id = request.POST.get("country_id")

        errors = []
        if not org_name:
            errors.append("Organization name is required.")
        contact_phone = request.POST.get("contact_phone", "").strip()
        if not contact_phone:
            errors.append("Contact phone is required.")
        elif not contact_phone.isdigit() or len(contact_phone) != 10:
            errors.append("Phone number must be exactly 10 digits.")
        if not country_id:
            errors.append("Country is required.")

        # Check subdomain availability
        subdomain = slugify(org_name)
        if not subdomain:
            errors.append("Organization name must contain valid characters.")
        elif Tenant.objects.filter(subdomain=subdomain).exists():
            errors.append(f"Subdomain '{subdomain}' is already taken. Try a different name.")

        if errors:
            data = {
                "org_name": org_name, "category": category,
                "contact_phone": request.POST.get("contact_phone", "").strip(),
                "country_id": country_id,
                "gst_number": request.POST.get("gst_number", "").strip(),
                "registration_number": request.POST.get("registration_number", "").strip(),
                "address": request.POST.get("address", "").strip(),
                "timezone": request.POST.get("timezone", "Asia/Kolkata"),
                "currency": request.POST.get("currency", "INR"),
                "language": request.POST.get("language", "en"),
                "date_format": request.POST.get("date_format", "DD/MM/YYYY"),
            }
            from apps.tenants.models import Category
            categories = Category.objects.filter(is_active=True).order_by('sort_order', 'name')
            countries = Country.objects.filter(status=True).order_by('name')
            return render(request, self.template_name, {
                "errors": errors, "data": data, "categories": categories, "countries": countries
            })

        # Save to session
        session_data = {
            "org_name": org_name,
            "category": category,
            "country_id": country_id,
            "contact_phone": request.POST.get("contact_phone", "").strip(),
            "gst_number": request.POST.get("gst_number", "").strip(),
            "registration_number": request.POST.get("registration_number", "").strip(),
            "address": request.POST.get("address", "").strip(),
            "timezone_id": request.POST.get("timezone_id"),
            "currency_id": request.POST.get("currency_id"),
            "language_id": request.POST.get("language_id"),
            "date_format_id": request.POST.get("date_format_id"),
            "subdomain": subdomain,
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
        org_data = request.session.get("onboarding_org")
        if not org_data:
            return redirect("/onboarding/")

        category_code = org_data.get("category")
        from apps.tenants.models import SubscriptionPlan, Feature, PlanFeature, PlanResourceLimit
        
        plans_qs = SubscriptionPlan.objects.filter(is_active=True).order_by('order', 'price')
        if category_code:
            plans_qs = plans_qs.filter(category__code=category_code)

        all_features = Feature.objects.filter(is_active=True).order_by('name')
        enriched_plans = []
        for p in plans_qs:
            assigned_feat_codes = set(PlanFeature.objects.filter(plan=p).values_list('feature__code', flat=True))
            res_limits = PlanResourceLimit.objects.filter(plan=p, resource__is_active=True).select_related('resource')
            
            plan_features = []
            for f in all_features:
                is_assigned = f.code in assigned_feat_codes
                plan_features.append({
                    "name": f.name,
                    "is_assigned": is_assigned,
                })
            
            enriched_plans.append({
                "plan": p,
                "features": plan_features,
                "resources": res_limits,
            })

        selected = request.session.get("onboarding_plan", {})
        return render(request, self.template_name, {
            "plans": enriched_plans,
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

        # Resolve Localization Objects for Summary
        country_obj = Country.objects.filter(pk=org_data.get("country_id")).first()
        currency_obj = Currency.objects.filter(pk=org_data.get("currency_id")).first() or (country_obj.primary_currency if country_obj else None)
        language_obj = Language.objects.filter(pk=org_data.get("language_id")).first() or (country_obj.primary_language if country_obj else None)
        timezone_obj = Timezone.objects.filter(pk=org_data.get("timezone_id")).first() or (country_obj.primary_timezone if country_obj else None)
        date_format_obj = DateFormat.objects.filter(pk=org_data.get("date_format_id")).first() or DateFormat.objects.filter(format_code="DD/MM/YYYY").first()

        return render(request, self.template_name, {
            "org": org_data,
            "plan": plan_data,
            "country": country_obj,
            "currency": currency_obj,
            "language": language_obj,
            "timezone": timezone_obj,
            "date_format": date_format_obj,
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
                schema_name=org_data["subdomain"],
                paid_until=trial_end.date(),
                on_trial=True,
            )

            # 2. Create Domain for subdomain routing
            request_host = request.get_host()
            base_host = request_host.split(":")[0]
            
            # Extract root domain from subdomain (e.g., test.localhost → localhost)
            parts = base_host.split(".")
            if len(parts) > 1 and parts[0] not in ("127", "localhost", "0"):
                root_host = ".".join(parts[1:])
            else:
                root_host = base_host
            
            # Can't have subdomains on IP addresses — use localhost instead
            if root_host in ("127.0.0.1", "0.0.0.0"):
                root_host = "localhost"
                
            tenant_domain = f"{org_data['subdomain']}.{root_host}"
            Domain.objects.create(
                domain=tenant_domain,
                tenant=client,
                is_primary=True,
            )

            # 3. Create Tenant record (app-level) and link to Client
            from apps.tenants.models import Category as TenantCategory
            from apps.core.models import Country, DateFormat
            category_obj = TenantCategory.objects.filter(code=org_data["category"]).first()
            country_obj = None
            if org_data.get("country_id"):
                try:
                    country_obj = Country.objects.get(pk=org_data["country_id"])
                except Country.DoesNotExist:
                    pass

            # Defaults for regional settings (use session choice or country primary)
            currency_obj = Currency.objects.filter(pk=org_data.get("currency_id")).first() or (country_obj.primary_currency if country_obj else None)
            language_obj = Language.objects.filter(pk=org_data.get("language_id")).first() or (country_obj.primary_language if country_obj else None)
            timezone_obj = Timezone.objects.filter(pk=org_data.get("timezone_id")).first() or (country_obj.primary_timezone if country_obj else None)
            
            # Date Format: use session choice or default to 'DD/MM/YYYY'
            date_format_obj = DateFormat.objects.filter(pk=org_data.get("date_format_id")).first() or DateFormat.objects.filter(format_code="DD/MM/YYYY").first()

            tenant = Tenant.objects.create(
                name=org_data["org_name"],
                category=category_obj,
                subdomain=org_data["subdomain"],
                phone=org_data.get("contact_phone", ""),
                country=country_obj,
                client=client,
                # New Consolidated Fields
                address=org_data.get("address", ""),
                gst_number=org_data.get("gst_number", ""),
                registration_number=org_data.get("registration_number", ""),
                timezone=timezone_obj,
                currency=currency_obj,
                language=language_obj,
                date_format=date_format_obj,
                working_hours={
                    "mon": {"open": "09:00", "close": "18:00"},
                    "tue": {"open": "09:00", "close": "18:00"},
                    "wed": {"open": "09:00", "close": "18:00"},
                    "thu": {"open": "09:00", "close": "18:00"},
                    "fri": {"open": "09:00", "close": "18:00"},
                    "sat": {"open": "09:00", "close": "14:00"},
                },
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

            # 5. Assign user to tenant and 'Owner' role (now implicit via is_owner)
            user = request.user
            user.tenant = tenant
            user.is_owner = True  # Primary account holder is always the owner
            
            admin_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Admin",
                defaults={"is_system_role": True},
            )
            # Admin gets every permission (still good to have for staff, owner has them implicitly)
            admin_role.permissions.set(Permission.objects.all())

            user.role = admin_role
            user.save(update_fields=["tenant", "role", "is_owner"])

            # 6. Send Welcome Email
            from django.core.mail import send_mail
            from django.conf import settings
            from django.template.loader import render_to_string

            context = {
                "user_name": user.get_full_name() or user.username,
                "user_email": user.email,
                "organization_name": tenant.name,
                "user_role": "Owner",  # Inform them they are the owner
                "dashboard_url": f"{request.scheme}://{tenant_domain}/dashboard/",
            }
            html_message = render_to_string("emails/welcome.html", context)

            try:
                send_mail(
                    subject=f"Welcome to Arogya — {tenant.name} is ready!",
                    message=f"Welcome aboard! Your workspace is ready.",
                    from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@arogya.com"),
                    recipient_list=[user.email],
                    html_message=html_message,
                )
            except Exception as e:
                logger.error(f"Failed to send welcome email to {user.email}: {e}")

            # 7. Seed default data is no longer needed in ClinicSettings
            # as it is all in Tenant model now.
            # Keeping schema_context for potential future tenant-specific seeds.
            # with schema_context(client.schema_name):
            #     pass

            # 8. Clean up session
            for key in ["onboarding_org", "onboarding_plan"]:
                request.session.pop(key, None)

            # 9. Redirect to tenant subdomain via auth bridge
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
