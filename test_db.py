import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.base')
django.setup()

from apps.tenants.models import SubscriptionPlan, Resource, Feature, PlanFeature, PlanResourceLimit

plan = SubscriptionPlan.objects.first()
print("Plan:", plan)
print("Features:", PlanFeature.objects.filter(plan=plan).values_list('feature__code', flat=True))
print("Limits:", list(PlanResourceLimit.objects.filter(plan=plan).values('resource__code', 'limit_value')))
