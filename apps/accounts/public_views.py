from django.views.generic import TemplateView
from apps.tenants.models import SubscriptionPlan


class LandingPageView(TemplateView):
    """Public landing page — marketing site for the Healthcare CRM."""
    template_name = "public/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["plans"] = SubscriptionPlan.objects.all().order_by("price")
        return ctx
