"""
seed_plans — Create the subscription plans, resources, and their mapped features using the dynamic architecture.

Usage:  python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import SubscriptionPlan, Feature, Resource, PlanResourceLimit, PlanFeature, Category

# ── Feature definitions ──────────────────────────────────────────────
FEATURES = [
    # (code, name, description)
    ("patients",        "Patient Management",     "Create, view, and manage patient records"),
    ("appointments",    "Appointment Scheduling",  "Book, manage, and track appointments"),
    ("billing",         "Basic Billing",           "Create invoices and collect payments"),
    ("prescriptions",   "Prescriptions",           "Create and print prescriptions as PDF"),
    ("clinical_notes",  "Clinical Notes",          "Doctor consultation notes (SOAP)"),
    ("staff",           "Staff Management",        "Manage employees and assign roles"),
    ("reports_basic",   "Basic Reports",           "Daily dashboard and basic statistics"),
    ("reports_advanced","Advanced Reports",        "Revenue analytics, doctor performance, trends"),
    ("sms",             "SMS Reminders",           "Send SMS appointment reminders"),
    ("whatsapp",        "WhatsApp Integration",    "Send messages via WhatsApp"),
    ("ai",              "AI Features",             "AI note generation, no-show prediction"),
    ("pharmacy",        "Pharmacy",                "Medicine catalog, inventory, sales"),
    ("lab",             "Lab",                     "Test catalog, sample tracking, reports"),
    ("analytics",       "Analytics Dashboard",     "Advanced analytics and visualizations"),
    ("export",          "Data Export",             "Export data to CSV/Excel"),
    ("communications",  "Communications",          "Message templates and campaigns"),
    ("notifications",   "Notifications",           "System notifications and alerts"),
    ("settings",        "Settings",                "Organization settings and configuration"),
    ("api_access",      "API Access",              "Access to REST API"),
    ("custom_branding", "Custom Branding",         "Remove watermark, custom colors"),
]

# ── Resource definitions ─────────────────────────────────────────────
RESOURCES = [
    ("MAX_DOCTORS", "Maximum Doctors"),
    ("MAX_STAFF", "Maximum Staff"),
    ("MAX_PATIENTS", "Maximum Patients"),
    ("MAX_APPOINTMENTS", "Maximum Appointments Per Month"),
]

# ── Plan definitions ───────────────────────────────────────────────
PLANS = [
    {
        "name": "FREE",
        "display_name": "Clinic Free",
        "price": 0,
        "description": "Solo doctor plan — run your clinic free with basic features.",
        "category_code": "CLINIC",
        "resources": {
            "MAX_DOCTORS": 1,
            "MAX_STAFF": 2,
            "MAX_PATIENTS": 300,
            "MAX_APPOINTMENTS": 150,
        },
        "features": [
            "patients", "appointments", "billing", "prescriptions",
            "clinical_notes", "reports_basic", "notifications", "settings",
        ],
    },
    {
        "name": "BASIC",
        "display_name": "Clinic Basic",
        "price": 999,
        "description": "For small clinics with up to 2 doctors.",
        "category_code": "CLINIC",
        "resources": {
            "MAX_DOCTORS": 2,
            "MAX_STAFF": 5,
            "MAX_PATIENTS": 2000,
            "MAX_APPOINTMENTS": 500,
        },
        "features": [
            "patients", "appointments", "billing", "prescriptions",
            "clinical_notes", "staff", "reports_basic",
            "notifications", "settings",
        ],
    },
    {
        "name": "GROWTH",
        "display_name": "Clinic Growth",
        "price": 2499,
        "description": "For growing multi-doctor clinics.",
        "category_code": "CLINIC",
        "resources": {
            "MAX_DOCTORS": 5,
            "MAX_STAFF": -1,  # unlimited
            "MAX_PATIENTS": 10000,
            "MAX_APPOINTMENTS": 2000,
        },
        "features": [
            "patients", "appointments", "billing", "prescriptions",
            "clinical_notes", "staff", "reports_basic", "reports_advanced",
            "sms", "pharmacy", "lab", "analytics", "export",
            "communications", "notifications", "settings",
        ],
    },
    {
        "name": "PRO",
        "display_name": "Clinic Pro",
        "price": 4999,
        "description": "Premium plan with AI, WhatsApp, and unlimited everything.",
        "category_code": "CLINIC",
        "resources": {
            "MAX_DOCTORS": -1,
            "MAX_STAFF": -1,
            "MAX_PATIENTS": -1,
            "MAX_APPOINTMENTS": -1,
        },
        "features": [
            "patients", "appointments", "billing", "prescriptions",
            "clinical_notes", "staff", "reports_basic", "reports_advanced",
            "sms", "whatsapp", "ai", "pharmacy", "lab", "analytics",
            "export", "communications", "notifications", "settings",
            "api_access", "custom_branding"
        ],
    },
]

class Command(BaseCommand):
    help = "Seed subscription plans, resources, and features into the database."

    def handle(self, *args, **options):
        # 1. Create features
        created_features = 0
        for code, name, description in FEATURES:
            _, created = Feature.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_active": True},
            )
            if created:
                created_features += 1

        self.stdout.write(f"  Features: {created_features} created, {len(FEATURES) - created_features} updated")

        # 2. Create resources
        resource_map = {}
        for code, name in RESOURCES:
            res, _ = Resource.objects.update_or_create(code=code, defaults={"name": name})
            resource_map[code] = res

        # 3. Create plans and link features & resources
        for plan_data in PLANS:
            feature_codes = plan_data.pop("features")
            resources_data = plan_data.pop("resources")
            
            category_code = plan_data.pop("category_code")
            cats = Category.objects.filter(code=category_code)
            category = cats.first() if cats.exists() else None

            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data["name"],
                defaults={**plan_data, "category": category},
            )

            # Link Features
            features = Feature.objects.filter(code__in=feature_codes)
            
            # Clear existing mapped features, then add them
            PlanFeature.objects.filter(plan=plan).delete()
            for feat in features:
                PlanFeature.objects.create(plan=plan, feature=feat)

            # Link Resources
            PlanResourceLimit.objects.filter(plan=plan).delete()
            for r_code, limit in resources_data.items():
                if r_code in resource_map:
                    PlanResourceLimit.objects.create(
                        plan=plan,
                        resource=resource_map[r_code],
                        limit_value=limit
                    )

            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} plan: {plan.display_name} ({features.count()} features, {len(resources_data)} limits)")

        self.stdout.write(self.style.SUCCESS("\n✅ Plans, Resources, and Features seeded successfully!"))
