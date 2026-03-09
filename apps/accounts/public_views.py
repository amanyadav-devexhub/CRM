from django.views.generic import TemplateView
from apps.tenants.models import SubscriptionPlan


class LandingPageView(TemplateView):
    """Public landing page — marketing site for the Healthcare CRM."""
    template_name = "public/landing.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from apps.tenants.models import SubscriptionPlan, Category, Feature, PlanFeature, PlanResourceLimit
        
        categories = Category.objects.filter(is_active=True).order_by('name')
        all_features = Feature.objects.filter(is_active=True).order_by('name')
        grouped_plans = []
        
        def build_p_data(query_set):
            p_data = []
            for p in query_set:
                assigned_feats = set(PlanFeature.objects.filter(plan=p).values_list('feature__code', flat=True))
                res = PlanResourceLimit.objects.filter(plan=p, resource__is_active=True).select_related('resource')
                
                plan_features = []
                for f in all_features:
                    is_assigned = f.code in assigned_feats
                    plan_features.append({
                        "name": f.name,
                        "li_class": "" if is_assigned else "disabled",
                        "icon": "check_circle" if is_assigned else "cancel"
                    })
                
                # Sort features: active first, then disabled
                plan_features.sort(key=lambda x: x['li_class'] != "")
                
                # Precalculate strings to prevent formatter breaking template tags
                display_billing = (p.billing_cycle.lower()[:-2] if p.billing_cycle else "month")
                display_desc = p.description if p.description else "Perfect for your healthcare practice"

                p_data.append({
                    "plan": p, 
                    "features": plan_features, 
                    "resources": res,
                    "display_billing": display_billing,
                    "display_desc": display_desc
                })
            return p_data

        # Load Global Plans (Plans with no specific category)
        global_plans = SubscriptionPlan.objects.filter(is_active=True, category__isnull=True).order_by("order", "price")
        if global_plans.exists():
            class PseudoGlobalCat:
                id = 0
                name = "Global Platform"
            
            p_data = build_p_data(global_plans)
            grouped_plans.append({"category": PseudoGlobalCat(), "plans": p_data})
            
        # Load Category-specific Plans
        for cat in categories:
            cat_plans = SubscriptionPlan.objects.filter(is_active=True, category=cat).order_by("order", "price")
            if cat_plans.exists():
                p_data = build_p_data(cat_plans)
                grouped_plans.append({"category": cat, "plans": p_data})
                
        ctx["grouped_plans"] = grouped_plans
        return ctx
