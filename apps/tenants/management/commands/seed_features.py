"""
seed_features — Populate Feature registry and link to SubscriptionPlans.

Usage:
    python manage.py seed_features
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import Feature, SubscriptionPlan


# ──────────────────────────────────────────────
# Master feature definitions
# ──────────────────────────────────────────────
FEATURES = [
    # (code, display name, description)
    ("patients",        "Patients",              "Patient registration & management"),
    ("appointments",    "Appointments",          "Appointment scheduling & calendar"),
    ("billing",         "Basic Billing",         "Invoice generation & payment tracking"),
    ("staff",           "Staff Management",      "Doctors, nurses & staff records"),
    ("reports_basic",   "Basic Reports",         "Standard operational reports"),
    ("queue",           "Queue / Tokens",        "Walk-in token & queue management"),
    ("clinical_notes",  "Clinical Notes",        "EMR / clinical documentation"),
    ("lab",             "Lab & Diagnostics",     "Lab orders, reports & integration"),
    ("pharmacy",        "Pharmacy",              "Pharmacy inventory & dispensing"),
    ("communications",  "Communications",        "Messages, campaigns & feedback"),
    ("notifications",   "Notifications",         "In-app & email notifications"),
    ("analytics",       "Advanced Analytics",    "Dashboards, trends & KPI reports"),
    ("ai_notes",        "AI Clinical Notes",     "AI-generated clinical documentation"),
    ("ai_risk",         "AI Risk Scoring",       "Predictive patient risk analysis"),
    ("multi_branch",    "Multi-Branch Mgmt",     "Multi-location management"),
]

# ──────────────────────────────────────────────
# Which features each plan includes
# ──────────────────────────────────────────────
PLAN_FEATURES = {
    "BASIC": [
        "patients", "appointments", "billing", "staff", "reports_basic",
    ],
    "PRO": [
        "patients", "appointments", "billing", "staff", "reports_basic",
        "queue", "clinical_notes", "lab", "pharmacy",
        "communications", "notifications",
    ],
    "ENTERPRISE": [
        "patients", "appointments", "billing", "staff", "reports_basic",
        "queue", "clinical_notes", "lab", "pharmacy",
        "communications", "notifications",
        "analytics", "ai_notes", "ai_risk", "multi_branch",
    ],
}


class Command(BaseCommand):
    help = "Seed Feature registry and link features to subscription plans."

    def handle(self, *args, **options):
        # 1. Create/update Feature records
        feature_objs = {}
        for code, name, desc in FEATURES:
            obj, created = Feature.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": desc, "is_active": True},
            )
            feature_objs[code] = obj
            tag = "[Created]" if created else "[Updated]"
            self.stdout.write(f"  {tag} feature: {code}")

        # 2. Link to plans
        for plan_name, codes in PLAN_FEATURES.items():
            try:
                plan = SubscriptionPlan.objects.get(name=plan_name)
            except SubscriptionPlan.DoesNotExist:
                self.stdout.write(self.style.WARNING(
                    f"  [WARNING] Plan '{plan_name}' not found - skipping."
                ))
                continue

            plan.features.set([feature_objs[c] for c in codes])
            self.stdout.write(self.style.SUCCESS(
                f"  [SUCCESS] {plan_name} -> {len(codes)} features linked"
            ))

        self.stdout.write(self.style.SUCCESS(
            f"\nDone - {len(FEATURES)} features seeded, "
            f"{len(PLAN_FEATURES)} plans wired."
        ))
