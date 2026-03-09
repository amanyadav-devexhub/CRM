import os, django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.tenants.models import SubscriptionPlan, Feature, PlanFeature, Resource, PlanResourceLimit
from django.test import Client

client = Client()
plan = SubscriptionPlan.objects.first()
print(f"Testing save on plan ID: {plan.id}")

res = client.post("/admin-plans/", {
    "action": "update_plan",
    "plan_id": plan.id,
    "price": "500",
    "billing_cycle": "MONTHLY",
    "display_name": plan.display_name,
    "category_id": "",
    "resource_MAX_DOCTORS": "5",
    "features": ["patients", "appointments"]
})

print("Status:", res.status_code)
# Now verify if saved
print("Features:", list(PlanFeature.objects.filter(plan=plan).values_list('feature__code', flat=True)))
print("Resource Limits:", list(PlanResourceLimit.objects.filter(plan=plan).values('resource__code', 'limit_value')))
