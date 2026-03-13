# apps/tenants/admin_views.py
"""
Admin panel views — SuperAdmin-only pages for managing
tenants, subscriptions, plans, features, categories, and platform settings.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.views import View
from django.contrib import messages
from .models import (
    Tenant, TenantSubscription, SubscriptionPlan,
    Feature, TenantFeature, Category,
)


class AdminCategoryListView(View):
    """Full CRUD for healthcare categories."""
    template_name = "dashboard/admin_categories.html"

    def get(self, request):
        q = request.GET.get("q", "").strip()
        categories = Category.objects.all()

        if q:
            categories = categories.filter(name__icontains=q) | categories.filter(code__icontains=q)

        cat_data = []
        for cat in categories:
            from django.db.models import Q
            tenant_count = Tenant.objects.filter(
                Q(category=cat.code) | Q(category_obj=cat)
            ).distinct().count()
            cat_data.append({
                "category": cat,
                "tenant_count": tenant_count,
            })

        # Editing support
        edit_id = request.GET.get("edit")
        editing = None
        if edit_id:
            try:
                editing = Category.objects.get(pk=edit_id)
            except Category.DoesNotExist:
                pass

        return render(request, self.template_name, {
            "cat_data": cat_data,
            "total": len(cat_data),
            "search_query": q,
            "editing": editing,
            "icon_choices": Category.ICON_CHOICES,
            "color_choices": Category.COLOR_CHOICES,
        })

    def post(self, request):
        action = request.POST.get("action")

        if action == "create":
            code = request.POST.get("code", "").strip().upper()
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            icon = request.POST.get("icon", "category")
            color = request.POST.get("color", "blue")
            sort_order = request.POST.get("sort_order", "0")

            if not code or not name:
                messages.error(request, "Code and Name are required.")
                return redirect("/admin-categories/")

            if Category.objects.filter(code=code).exists():
                messages.error(request, f"Category with code '{code}' already exists.")
                return redirect("/admin-categories/")

            try:
                Category.objects.create(
                    code=code,
                    name=name,
                    description=description,
                    icon=icon,
                    color=color,
                    sort_order=int(sort_order) if sort_order else 0,
                )
                messages.success(request, f"Category '{name}' created successfully.")
            except Exception as e:
                messages.error(request, f"Error creating category: {e}")

            return redirect("/admin-categories/")

        cat_id = request.POST.get("category_id")
        try:
            cat = Category.objects.get(pk=cat_id)
        except Category.DoesNotExist:
            messages.error(request, "Category not found.")
            return redirect("/admin-categories/")

        if action == "update":
            cat.name = request.POST.get("name", cat.name).strip()
            cat.description = request.POST.get("description", cat.description).strip()
            cat.icon = request.POST.get("icon", cat.icon)
            cat.color = request.POST.get("color", cat.color)
            sort_order = request.POST.get("sort_order", str(cat.sort_order))
            cat.sort_order = int(sort_order) if sort_order else cat.sort_order
            cat.save()
            messages.success(request, f"Category '{cat.name}' updated.")

        elif action == "activate":
            cat.is_active = True
            cat.save(update_fields=["is_active"])
            messages.success(request, f"'{cat.name}' activated.")

        elif action == "deactivate":
            cat.is_active = False
            cat.save(update_fields=["is_active"])
            messages.success(request, f"'{cat.name}' deactivated.")

        elif action == "delete":
            tenant_count = Tenant.objects.filter(
                Q(category=cat.code) | Q(category_obj=cat)
            ).distinct().count()
            if tenant_count > 0:
                messages.error(request, f"Cannot delete '{cat.name}' — {tenant_count} tenant(s) are using it. Deactivate it instead.")
            else:
                name = cat.name
                cat.delete()
                messages.success(request, f"Category '{name}' deleted permanently.")

        return redirect("/admin-categories/")

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
    """List and edit subscription plans, resources, and features."""
    template_name = "dashboard/admin_plans.html"

    def get(self, request):
        from django.db import models
        from .models import SubscriptionPlan, TenantSubscription, Category, Feature, Resource, PlanFeature, PlanResourceLimit
        
        selected_category_id = request.GET.get('category')
        plans = SubscriptionPlan.objects.all().select_related('category').order_by('order', 'price')
        
        if selected_category_id:
            if selected_category_id == "global":
                plans = plans.filter(category__isnull=True)
            else:
                plans = plans.filter(category_id=selected_category_id)
        
        master_features = Feature.objects.all().order_by('name')
        master_resources = Resource.objects.all().order_by('name')
        
        all_features = master_features
        all_resources = master_resources
        
        if selected_category_id:
            if selected_category_id == "global":
                all_features = all_features.filter(category__isnull=True)
                all_resources = all_resources.filter(category__isnull=True)
            else:
                all_features = all_features.filter(category_id=selected_category_id)
                all_resources = all_resources.filter(category_id=selected_category_id)
        
        # Pre-calculate category selection to avoid formatter issues with == in templates
        categories_list = []
        for cat in Category.objects.all():
            categories_list.append({
                "pk": cat.pk,
                "name": cat.name,
                "is_selected": str(cat.pk) == str(selected_category_id)
            })
        
        plan_data = []
        for p in plans:
            sub_count = TenantSubscription.objects.filter(plan=p).count()
            
            # Get assigned feature codes
            assigned_feats = set(PlanFeature.objects.filter(plan=p).values_list('feature__code', flat=True))
            
            # Get resource limits map: {resource_code: limit_value}
            res_limits = PlanResourceLimit.objects.filter(plan=p)
            limit_map = {rl.resource.code: rl.limit_value for rl in res_limits}
            
            # Filter resources: Global (no category) OR match plan category
            relevant_resources = master_resources.filter(
                models.Q(category__isnull=True) | models.Q(category=p.category)
            )
            
            p_resources = []
            for r in relevant_resources:
                val = limit_map.get(r.code, "")
                p_resources.append({"resource": r, "value": val})
                
            # Filter features: Global (no category) OR match plan category
            relevant_features = master_features.filter(
                models.Q(category__isnull=True) | models.Q(category=p.category)
            )
            
            p_features = []
            for f in relevant_features:
                is_assigned = f.code in assigned_feats
                p_features.append({
                    "feature": f, 
                    "is_assigned": is_assigned,
                    "checked_str": "checked" if is_assigned else ""
                })

            # Precalculate selected choices to subvert linter bugs with == in templates
            p_billing_options = []
            for bc in SubscriptionPlan.BILLING_CHOICES:
                p_billing_options.append({
                    "value": bc[0], 
                    "label": bc[1], 
                    "selected_str": "selected" if p.billing_cycle == bc[0] else ""
                })

            p_category_options = []
            for cat in categories_list:
                p_category_options.append({
                    "pk": cat['pk'], 
                    "name": cat['name'], 
                    "selected_str": "selected" if p.category_id == cat['pk'] else ""
                })
            
            plan_data.append({
                "plan": p, 
                "subscriber_count": sub_count,
                "resources": p_resources,
                "features": p_features,
                "billing_options": p_billing_options,
                "category_options": p_category_options,
            })

        return render(request, self.template_name, {
            "plan_data": plan_data,
            "total_plans": len(plan_data),
            "total_features": all_features.count(),
            "total_resources": all_resources.count(),
            "categories": categories_list,
            "billing_choices": SubscriptionPlan.BILLING_CHOICES,
            "all_features": all_features,
            "all_resources": all_resources,
            "selected_category": selected_category_id,
            "is_global_selected": selected_category_id == "global",
        })

    def post(self, request):
        from .models import SubscriptionPlan, Category, Feature, Resource, PlanFeature, PlanResourceLimit
        
        action = request.POST.get("action")
        active_tab = request.POST.get("active_tab", "plans")
        redirect_url = f"/admin-plans/?tab={active_tab}"
        
        # Add category if present to maintain filter
        selected_category = request.POST.get("redirect_category") or request.GET.get("category")
        if selected_category:
            redirect_url += f"&category={selected_category}"

        # ── Feature Management ──
        if action == "create_feature":
            code = request.POST.get("code", "").strip().lower()
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            cat_id = request.POST.get("category_id")
            if code and name:
                try:
                    cat = Category.objects.get(pk=cat_id) if cat_id else None
                    Feature.objects.create(code=code, name=name, description=desc, category=cat)
                    messages.success(request, f"Feature '{name}' created.")
                except Exception as e:
                    messages.error(request, f"Error creating feature: {str(e)}")
            else:
                messages.error(request, "Feature code and name are required.")
            return redirect(redirect_url)
            
        elif action == "delete_feature":
            feature_id = request.POST.get("feature_id")
            Feature.objects.filter(id=feature_id).delete()
            messages.success(request, "Feature deleted.")
            return redirect(redirect_url)

        elif action == "toggle_feature":
            feature_id = request.POST.get("feature_id")
            feat = Feature.objects.get(id=feature_id)
            feat.is_active = not feat.is_active
            feat.save()
            status = "activated" if feat.is_active else "deactivated"
            messages.success(request, f"Feature '{feat.name}' {status}.")
            return redirect(redirect_url)
            
        elif action == "update_feature":
            feature_id = request.POST.get("feature_id")
            name = request.POST.get("name", "").strip()
            desc = request.POST.get("description", "").strip()
            cat_id = request.POST.get("category_id")
            if name:
                feat = Feature.objects.get(id=feature_id)
                feat.name = name
                feat.description = desc
                feat.category = Category.objects.get(pk=cat_id) if cat_id else None
                feat.save()
                messages.success(request, f"Feature '{name}' updated.")
            return redirect(redirect_url)
            
        # ── Resource Management ──
        elif action == "create_resource":
            code = request.POST.get("code", "").strip().upper()
            name = request.POST.get("name", "").strip()
            cat_id = request.POST.get("category_id")
            if code and name:
                try:
                    cat = Category.objects.get(pk=cat_id) if cat_id else None
                    Resource.objects.create(code=code, name=name, category=cat)
                    messages.success(request, f"Resource '{name}' created.")
                except Exception as e:
                    messages.error(request, f"Error creating resource: {str(e)}")
            else:
                messages.error(request, "Resource code and name are required.")
            return redirect(redirect_url)
            
        elif action == "delete_resource":
            resource_id = request.POST.get("resource_id")
            Resource.objects.filter(id=resource_id).delete()
            messages.success(request, "Resource deleted.")
            return redirect(redirect_url)

        elif action == "toggle_resource":
            resource_id = request.POST.get("resource_id")
            res = Resource.objects.get(id=resource_id)
            res.is_active = not res.is_active
            res.save()
            status = "activated" if res.is_active else "deactivated"
            messages.success(request, f"Resource '{res.name}' {status}.")
            return redirect(redirect_url)

        elif action == "update_resource":
            resource_id = request.POST.get("resource_id")
            name = request.POST.get("name", "").strip()
            cat_id = request.POST.get("category_id")
            if name:
                res = Resource.objects.get(id=resource_id)
                res.name = name
                res.category = Category.objects.get(pk=cat_id) if cat_id else None
                res.save()
                messages.success(request, f"Resource '{name}' updated.")
            return redirect(redirect_url)
            
        # ── Plan Management ──
        plan_id = request.POST.get("plan_id")

        if action == "create_plan":
            name = request.POST.get("name", "").strip().upper()
            display_name = request.POST.get("display_name", "").strip()
            price = request.POST.get("price", "0")
            try:
                order = int(request.POST.get("order") or 0)
            except ValueError:
                order = 0
            category_id = request.POST.get("category_id")
            billing_cycle = request.POST.get("billing_cycle", "MONTHLY")

            if name and display_name:
                try:
                    category = Category.objects.get(pk=category_id) if category_id else None
                    plan = SubscriptionPlan.objects.create(
                        name=name,
                        display_name=display_name,
                        price=price,
                        order=order,
                        category=category,
                        billing_cycle=billing_cycle,
                        is_active='is_active' in request.POST
                    )
                    
                    # Process selected features
                    for feat_str in request.POST.getlist("features"):
                        try:
                            feat = Feature.objects.get(code=feat_str)
                            PlanFeature.objects.create(plan=plan, feature=feat)
                        except Feature.DoesNotExist:
                            pass
                    
                    # Force save again to trigger post_save signal after features/resources are linked
                    plan.save()
                    messages.success(request, f"Plan '{display_name}' created.")
                except Exception as e:
                    messages.error(request, f"Error creating plan: {str(e)}")
            
            return redirect(redirect_url)
            
        elif action == "update_plan" and plan_id:
            try:
                plan = SubscriptionPlan.objects.get(pk=plan_id)
                plan.display_name = request.POST.get("display_name")
                plan.price = request.POST.get("price")
                plan.order = int(request.POST.get("order") or 0)
                plan.billing_cycle = request.POST.get("billing_cycle")
                # Handle is_active status from checkbox
                plan.is_active = 'is_active' in request.POST
                
                # Update features
                PlanFeature.objects.filter(plan=plan).delete()
                for feat_str in request.POST.getlist("features"):
                    try:
                        feat = Feature.objects.get(code=feat_str)
                        PlanFeature.objects.create(plan=plan, feature=feat)
                    except Feature.DoesNotExist:
                        pass
                
                # Update resources
                for key, value in request.POST.items():
                    if key.startswith("res_") and value.strip():
                        res_code = key.replace("res_", "")
                        try:
                            resource = Resource.objects.get(code=res_code)
                            PlanResourceLimit.objects.update_or_create(
                                plan=plan, resource=resource,
                                defaults={'limit_value': value}
                            )
                        except Resource.DoesNotExist:
                            pass

                # Force save to trigger post_save signal after features/resources are modified
                plan.save()
                messages.success(request, f"Plan '{plan.display_name}' updated.")
            except Exception as e:
                messages.error(request, f"Error updating plan: {str(e)}")
            
            return redirect(redirect_url)

        elif action == "delete_plan" and plan_id:
            SubscriptionPlan.objects.filter(id=plan_id).delete()
            messages.success(request, "Plan archived and removed.")
            return redirect(redirect_url)

        return redirect(redirect_url)
    
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


class AdminRolesPermissionsView(View):
    """SuperAdmin view for managing global permissions and category-scoped roles."""
    template_name = "dashboard/admin_roles.html"

    def get(self, request):
        from apps.accounts.models import Permission
        from apps.tenants.models import CategoryRoleTemplate, Category

        # ── Permissions tab data ──
        all_permissions = Permission.objects.all().order_by("code")
        grouped_perms = {}
        for p in all_permissions:
            prefix = p.code.split(".")[0]
            if prefix not in grouped_perms:
                grouped_perms[prefix] = []
            grouped_perms[prefix].append(p)

        # ── Roles tab data ──
        all_categories = Category.objects.all().order_by("name")
        selected_category_id = request.GET.get("category")
        selected_category = None
        roles = []
        role_data = []

        if selected_category_id:
            try:
                selected_category = Category.objects.get(pk=selected_category_id)
                roles = CategoryRoleTemplate.objects.filter(category=selected_category).order_by("name")

                for role in roles:
                    role_perm_ids = set(role.permissions.values_list("id", flat=True))
                    # RoleTemplates don't directly have users. To determine "in use", you'd query tenants using this category and this role.
                    # For simplicity in this view, we'll just show 0 or handle logic differently.
                    role_data.append({
                        "role": role,
                        "user_count": 0, # Templates don't directly map to users here
                        "perm_ids": role_perm_ids,
                    })
            except Category.DoesNotExist:
                pass

        # Build category options with selection state
        category_options = []
        for c in all_categories:
            category_options.append({
                "pk": str(c.pk),
                "name": c.name,
                "is_selected": str(c.pk) == str(selected_category_id),
            })

        active_tab = request.GET.get("tab", "roles") # Default to roles

        return render(request, self.template_name, {
            "grouped_perms": grouped_perms,
            "total_permissions": all_permissions.count(),
            "all_permissions": all_permissions,
            "category_options": category_options,
            "selected_category": selected_category,
            "role_data": role_data,
            "total_roles": len(role_data),
            "active_tab": active_tab,
        })

    def post(self, request):
        from apps.accounts.models import Permission
        from apps.tenants.models import CategoryRoleTemplate, Category
        
        action = request.POST.get("action")
        active_tab = request.POST.get("active_tab", "roles")
        selected_category_id = request.POST.get("selected_category_id", "")

        redirect_url = f"/admin-roles/?tab={active_tab}"
        if active_tab == "roles" and selected_category_id:
            redirect_url += f"&category={selected_category_id}"

        # ── Permission CRUD ──
        if action == "create_permission":
            code = request.POST.get("code", "").strip().lower()
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            if code and name:
                if Permission.objects.filter(code=code).exists():
                    messages.error(request, f"Permission '{code}' already exists.")
                else:
                    Permission.objects.create(code=code, name=name, description=description)
                    messages.success(request, f"Permission '{name}' created.")
            else:
                messages.error(request, "Code and name are required.")
            return redirect(redirect_url)

        elif action == "delete_permission":
            perm_id = request.POST.get("permission_id")
            try:
                perm = Permission.objects.get(pk=perm_id)
                # Check if any role is using this permission
                role_count = perm.roles.count()
                template_count = perm.categoryroletemplate_set.count()
                if role_count > 0 or template_count > 0:
                    messages.error(request, f"Cannot delete '{perm.name}' — it's assigned to {role_count} role(s) and {template_count} template(s). Remove it first.")
                else:
                    name = perm.name
                    perm.delete()
                    messages.success(request, f"Permission '{name}' deleted.")
            except Permission.DoesNotExist:
                messages.error(request, "Permission not found.")
            return redirect(redirect_url)
            
        elif action == "update_permission":
            perm_id = request.POST.get("permission_id")
            name = request.POST.get("name", "").strip()
            description = request.POST.get("description", "").strip()
            if name:
                try:
                    perm = Permission.objects.get(pk=perm_id)
                    perm.name = name
                    perm.description = description
                    perm.save(update_fields=["name", "description"])
                    messages.success(request, f"Permission '{name}' updated.")
                except Permission.DoesNotExist:
                    messages.error(request, "Permission not found.")
            else:
                messages.error(request, "Permission name is required.")
            return redirect(redirect_url)

        # ── Role Template CRUD ──
        elif action == "create_role":
            category_id = request.POST.get("category_id")
            role_name = request.POST.get("role_name", "").strip()
            role_code = request.POST.get("role_code", "").strip()
            role_desc = request.POST.get("role_desc", "").strip()
            is_active = request.POST.get("is_active") == "on"
            
            if not category_id or not role_name:
                messages.error(request, "Category and role name are required.")
                return redirect(redirect_url)
            try:
                category = Category.objects.get(pk=category_id)
                if CategoryRoleTemplate.objects.filter(category=category, name=role_name).exists():
                    messages.error(request, f"Role '{role_name}' already exists for {category.name}.")
                else:
                    selected_perms = request.POST.getlist("permissions")
                    role_template = CategoryRoleTemplate.objects.create(
                        category=category, 
                        name=role_name, 
                        code=role_code,
                        description=role_desc,
                        is_active=is_active
                    )
                    if selected_perms:
                        role_template.permissions.set(selected_perms)
                    messages.success(request, f"Role '{role_name}' created for {category.name}.")
            except Category.DoesNotExist:
                messages.error(request, "Category not found.")
            return redirect(redirect_url)

        elif action == "update_role":
            role_id = request.POST.get("role_id")
            try:
                role_template = CategoryRoleTemplate.objects.get(pk=role_id)
                selected_perms = request.POST.getlist("permissions")
                role_template.permissions.set(selected_perms)

                new_name = request.POST.get("role_name", "").strip()
                new_code = request.POST.get("role_code", "").strip()
                new_desc = request.POST.get("role_desc", "").strip()
                is_active = request.POST.get("is_active") == "on"

                if new_name:
                    role_template.name = new_name
                role_template.code = new_code
                role_template.description = new_desc
                role_template.is_active = is_active
                role_template.save(update_fields=["name", "code", "description", "is_active"])

                messages.success(request, f"Role '{role_template.name}' updated.")
            except CategoryRoleTemplate.DoesNotExist:
                messages.error(request, "Role not found.")
            return redirect(redirect_url)

        elif action == "delete_role":
            role_id = request.POST.get("role_id")
            try:
                role_template = CategoryRoleTemplate.objects.get(pk=role_id)
                name = role_template.name
                role_template.delete()
                messages.success(request, f"Role '{name}' deleted.")
            except CategoryRoleTemplate.DoesNotExist:
                messages.error(request, "Role not found.")
            return redirect(redirect_url)

        return redirect(redirect_url)
