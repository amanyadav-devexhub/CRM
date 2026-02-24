"""
seed_plans — Create the 4 subscription plans and their mapped features.

Usage:  python manage.py seed_plans
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import SubscriptionPlan, Feature


# ── Feature definitions ──────────────────────────────────────────────
FEATURES = [
    # (code, display_name, description)
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
    ("pharmacy",        "Pharmacy Add-on",         "Medicine catalog, inventory, sales"),
    ("lab",             "Lab Add-on",              "Test catalog, sample tracking, reports"),
    ("analytics",       "Analytics Dashboard",     "Advanced analytics and visualizations"),
    ("export",          "Data Export",             "Export data to CSV/Excel"),
    ("communications",  "Communications",          "Message templates and campaigns"),
    ("notifications",   "Notifications",           "System notifications and alerts"),
    ("settings",        "Settings",                "Organization settings and configuration"),
]

# ── Plan definitions ───────────────────────────────────────────────
PLANS = [
    {
        "name": "FREE",
        "display_name": "Clinic Free",
        "price": 0,
        "description": "Solo doctor plan — run your clinic free with basic features.",
        "max_doctors": 1,
        "max_staff": 2,
        "max_patients": 300,
        "max_appointments_per_month": 150,
        "sms_enabled": False,
        "whatsapp_enabled": False,
        "ai_enabled": False,
        "export_enabled": False,
        "custom_branding": False,
        "api_access": False,
        "advanced_reports": False,
        "pharmacy_addon": False,
        "lab_addon": False,
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
        "max_doctors": 2,
        "max_staff": 5,
        "max_patients": 2000,
        "max_appointments_per_month": 500,
        "sms_enabled": False,
        "whatsapp_enabled": False,
        "ai_enabled": False,
        "export_enabled": False,
        "custom_branding": False,
        "api_access": False,
        "advanced_reports": False,
        "pharmacy_addon": False,
        "lab_addon": False,
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
        "max_doctors": 5,
        "max_staff": 99999,  # unlimited
        "max_patients": 10000,
        "max_appointments_per_month": 2000,
        "sms_enabled": True,
        "whatsapp_enabled": False,
        "ai_enabled": False,
        "export_enabled": True,
        "custom_branding": False,
        "api_access": False,
        "advanced_reports": True,
        "pharmacy_addon": True,
        "lab_addon": True,
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
        "max_doctors": 99999,
        "max_staff": 99999,
        "max_patients": 99999,
        "max_appointments_per_month": 99999,
        "sms_enabled": True,
        "whatsapp_enabled": True,
        "ai_enabled": True,
        "export_enabled": True,
        "custom_branding": True,
        "api_access": True,
        "advanced_reports": True,
        "pharmacy_addon": True,
        "lab_addon": True,
        "features": [
            "patients", "appointments", "billing", "prescriptions",
            "clinical_notes", "staff", "reports_basic", "reports_advanced",
            "sms", "whatsapp", "ai", "pharmacy", "lab", "analytics",
            "export", "communications", "notifications", "settings",
        ],
    },
]


class Command(BaseCommand):
    help = "Seed subscription plans and features into the database."

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

        # 2. Create plans and link features
        for plan_data in PLANS:
            feature_codes = plan_data.pop("features")
            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data["name"],
                defaults=plan_data,
            )

            # Link features
            features = Feature.objects.filter(code__in=feature_codes)
            plan.features.set(features)

            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} plan: {plan.display_name} ({features.count()} features)")

        self.stdout.write(self.style.SUCCESS("\n✅ Plans and features seeded successfully!"))
