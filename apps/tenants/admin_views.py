# apps/tenants/admin_views.py
"""
Admin panel views — SuperAdmin-only pages for managing
tenants, subscriptions, plans, features, and platform settings.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages
from .models import (
    Tenant, TenantSubscription, SubscriptionPlan,
    Feature, TenantFeature,
)


class AdminTenantListView(View):
    """List all tenants with search, activate/deactivate, delete."""
    template_name = "dashboard/admin_tenants.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        tenants = Tenant.objects.all().order_by("-created_at")

        if q:
            tenants = tenants.filter(name__icontains=q) | tenants.filter(subdomain__icontains=q)

        # Attach subscription info
        tenant_data = []
        for t in tenants:
            sub = TenantSubscription.objects.filter(tenant=t).first()
            tenant_data.append({
                "tenant": t,
                "subscription": sub,
                "plan_name": (sub.plan.display_name or sub.plan.name) if sub else "—",
                "sub_status": sub.status if sub else "—",
            })

        # Pagination setup (10 tenants per page)
        paginator = Paginator(tenant_data, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {
            "tenant_data": page_obj,
            "search_query": q,
            "total": len(tenant_data),
        })

    def post(self, request):
        action = request.POST.get("action")
        tenant_id = request.POST.get("tenant_id")

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            messages.error(request, "Tenant not found.")
            return redirect("/admin-tenants/")

        if action == "activate":
            tenant.is_active = True
            tenant.save(update_fields=["is_active"])
            messages.success(request, f"{tenant.name} activated.")
        elif action == "deactivate":
            tenant.is_active = False
            tenant.save(update_fields=["is_active"])
            messages.success(request, f"{tenant.name} deactivated.")
        elif action == "delete":
            name = tenant.name
            tenant.is_active = False
            tenant.save(update_fields=["is_active"])
            
            # Optionally set their subscription to cancelled as well
            sub = getattr(tenant, 'subscription', None)
            if sub:
                sub.status = 'CANCELLED'
                sub.save(update_fields=['status'])
                
            messages.success(request, f"{name} has been soft-deleted (deactivated and subscription cancelled).")

        return redirect("/admin-tenants/")


class AdminSubscriptionListView(View):
    """List all subscriptions with status management."""
    template_name = "dashboard/admin_subscriptions.html"

    STATUS_CHOICES = ["ACTIVE", "TRIAL", "EXPIRED", "SUSPENDED", "CANCELLED"]

    def get(self, request):
        subs = TenantSubscription.objects.select_related(
            "tenant", "plan"
        ).order_by("-created_at")

        # Pagination setup (10 subscriptions per page)
        paginator = Paginator(subs, 10)
        page_number = request.GET.get('page', 1)
        page_obj = paginator.get_page(page_number)

        return render(request, self.template_name, {
            "subscriptions": page_obj,
            "status_choices": self.STATUS_CHOICES,
            "total": subs.count(),
        })

    def post(self, request):
        action = request.POST.get("action")
        sub_id = request.POST.get("sub_id")

        try:
            sub = TenantSubscription.objects.get(pk=sub_id)
        except TenantSubscription.DoesNotExist:
            messages.error(request, "Subscription not found.")
            return redirect("/admin-subscriptions/")

        if action == "change_status":
            new_status = request.POST.get("new_status")
            if new_status in self.STATUS_CHOICES:
                sub.status = new_status
                sub.save(update_fields=["status"])
                messages.success(request, f"Subscription for {sub.tenant.name} → {new_status}")

        return redirect("/admin-subscriptions/")


class AdminPlanListView(View):
    """List and edit subscription plans."""
    template_name = "dashboard/admin_plans.html"

    def get(self, request):
        plans = SubscriptionPlan.objects.filter(is_active=True)
        plan_data = []
        for p in plans:
            sub_count = TenantSubscription.objects.filter(plan=p).count()
            plan_data.append({"plan": p, "subscriber_count": sub_count})

        return render(request, self.template_name, {
            "plan_data": plan_data,
            "total": len(plan_data),
        })

    def post(self, request):
        action = request.POST.get("action")
        plan_id = request.POST.get("plan_id")

        if action == "create":
            name = request.POST.get("name", "").strip().upper()
            display_name = request.POST.get("display_name", "").strip()
            price = request.POST.get("price", "0")
            max_doctors = request.POST.get("max_doctors", "1")
            max_staff = request.POST.get("max_staff", "2")
            max_patients = request.POST.get("max_patients", "300")
            max_appointments = request.POST.get("max_appointments", "150")

            if name and display_name:
                try:
                    SubscriptionPlan.objects.create(
                        name=name,
                        display_name=display_name,
                        price=price,
                        max_doctors=max_doctors,
                        max_staff=max_staff,
                        max_patients=max_patients,
                        max_appointments_per_month=max_appointments
                    )
                    messages.success(request, f"Plan '{display_name}' created successfully.")
                except Exception as e:
                    messages.error(request, f"Error creating plan: {e}")
            else:
                messages.error(request, "Name and Display Name are required.")
            
            return redirect("/admin-plans/")

        try:
            plan = SubscriptionPlan.objects.get(pk=plan_id)
        except SubscriptionPlan.DoesNotExist:
            messages.error(request, "Plan not found.")
            return redirect("/admin-plans/")

        if action == "update":
            plan.price = request.POST.get("price", plan.price)
            plan.max_doctors = request.POST.get("max_doctors", plan.max_doctors)
            plan.max_staff = request.POST.get("max_staff", plan.max_staff)
            plan.max_patients = request.POST.get("max_patients", plan.max_patients)
            plan.max_appointments_per_month = request.POST.get(
                "max_appointments", plan.max_appointments_per_month
            )
            plan.save()
            messages.success(request, f"{plan.display_name} plan updated.")
        elif action == "delete":
            plan.is_active = False
            plan.save(update_fields=["is_active"])
            messages.success(request, f"{plan.display_name} plan soft-deleted.")

        return redirect("/admin-plans/")


class AdminFeatureListView(View):
    """List features with toggle and create/delete."""
    template_name = "dashboard/admin_features.html"

    def get(self, request):
        features = Feature.objects.all().order_by("name")
        feature_data = []

        # Get all distinct categories dynamically if possible, or use the model choices
        categories = dict(Tenant.CATEGORY_CHOICES).keys()

        for f in features:
            category_counts = {}
            total_count = 0

            for cat in categories:
                # Count tenants of this category that have this feature enabled
                count = TenantFeature.objects.filter(
                    feature_name=f.code,
                    is_enabled=True,
                    tenant__category=cat
                ).count()
                
                if count > 0:
                    category_counts[cat] = count
                total_count += count

            feature_data.append({
                "feature": f, 
                "total_count": total_count,
                "category_counts": category_counts
            })

        return render(request, self.template_name, {
            "feature_data": feature_data,
            "total": len(feature_data),
        })

    def post(self, request):
        action = request.POST.get("action")

        if action == "toggle":
            feature_id = request.POST.get("feature_id")
            try:
                feature = Feature.objects.get(pk=feature_id)
                feature.is_active = not feature.is_active
                feature.save(update_fields=["is_active"])
                state = "enabled" if feature.is_active else "disabled"
                messages.success(request, f"{feature.name} {state}.")
            except Feature.DoesNotExist:
                messages.error(request, "Feature not found.")

        elif action == "create":
            code = request.POST.get("code", "").strip()
            name = request.POST.get("name", "").strip()
            if code and name:
                Feature.objects.get_or_create(
                    code=code, defaults={"name": name, "is_active": True}
                )
                messages.success(request, f"Feature '{name}' created.")
            else:
                messages.error(request, "Code and name are required.")

        elif action == "delete":
            feature_id = request.POST.get("feature_id")
            try:
                feature = Feature.objects.get(pk=feature_id)
                name = feature.name
                feature.delete()
                messages.success(request, f"{name} deleted.")
            except Feature.DoesNotExist:
                messages.error(request, "Feature not found.")

        return redirect("/admin-features/")


class AdminSettingsView(View):
    """Platform settings page."""
    template_name = "dashboard/admin_settings.html"

    def get(self, request):
        return render(request, self.template_name, {
            "tenant_count": Tenant.objects.count(),
            "feature_count": Feature.objects.count(),
            "plan_count": SubscriptionPlan.objects.count(),
        })


class AdminAnalyticsView(View):
    """Global analytics — tenant distribution, subscription stats."""
    template_name = "dashboard/admin_analytics.html"

    def get(self, request):
        from django.db.models import Count

        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(is_active=True).count()
        inactive_tenants = total_tenants - active_tenants

        # Category breakdown
        category_stats = (
            Tenant.objects.values("category")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Subscription status breakdown
        sub_stats = (
            TenantSubscription.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Plan popularity
        plan_stats = (
            TenantSubscription.objects.values("plan__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # Feature adoption
        total_features = Feature.objects.count()
        active_features = Feature.objects.filter(is_active=True).count()

        return render(request, self.template_name, {
            "total_tenants": total_tenants,
            "active_tenants": active_tenants,
            "inactive_tenants": inactive_tenants,
            "category_stats": category_stats,
            "sub_stats": sub_stats,
            "plan_stats": plan_stats,
            "total_features": total_features,
            "active_features": active_features,
        })


class AdminRevenueView(View):
    """Revenue overview — plan pricing, subscriber counts, MRR estimates."""
    template_name = "dashboard/admin_revenue.html"

    def get(self, request):
        from django.db.models import Sum, Count, F

        plans = SubscriptionPlan.objects.all()
        revenue_data = []
        total_mrr = 0

        for plan in plans:
            active_subs = TenantSubscription.objects.filter(
                plan=plan, status__in=["ACTIVE", "TRIAL"]
            ).count()
            mrr = float(plan.price) * active_subs
            total_mrr += mrr
            revenue_data.append({
                "plan": plan,
                "active_subs": active_subs,
                "mrr": mrr,
            })

        total_subs = TenantSubscription.objects.count()
        active_subs = TenantSubscription.objects.filter(
            status__in=["ACTIVE", "TRIAL"]
        ).count()
        churned = TenantSubscription.objects.filter(
            status__in=["CANCELLED", "EXPIRED"]
        ).count()

        return render(request, self.template_name, {
            "revenue_data": revenue_data,
            "total_mrr": total_mrr,
            "total_subs": total_subs,
            "active_subs": active_subs,
            "churned": churned,
        })

class AdminTenantDetailView(View):
    """View details of a specific tenant."""
    template_name = "dashboard/admin_tenant_detail.html"

    def get(self, request, pk):
        tenant = get_object_or_404(Tenant, pk=pk)
        subscription = TenantSubscription.objects.filter(tenant=tenant).first()
        return render(request, self.template_name, {
            "tenant": tenant,
            "subscription": subscription,
        })

