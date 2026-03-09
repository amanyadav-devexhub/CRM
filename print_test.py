import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.tenants.admin_views import AdminPlanListView
from django.test import RequestFactory
from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.middleware import SessionMiddleware
from apps.tenants.models import SubscriptionPlan, Feature, PlanFeature, Resource, PlanResourceLimit

plan = SubscriptionPlan.objects.first()

factory = RequestFactory()
request = factory.post("/admin-plans/", {
    "action": "update_plan",
    "plan_id": plan.id,
    "price": "500",
    "billing_cycle": "MONTHLY",
    "display_name": plan.display_name,
    "category_id": "",
    "resource_MAX_DOCTORS": "5",
    "features": ["patients", "appointments"]
})

middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()
setattr(request, '_messages', FallbackStorage(request))

view = AdminPlanListView.as_view()
response = view(request)

print("Features:", list(PlanFeature.objects.filter(plan=plan).values_list('feature__code', flat=True)))
