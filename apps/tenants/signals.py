from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.core.cache import cache
from apps.tenants.models import TenantFeature, PlanFeature, SubscriptionPlan, TenantSubscription, Tenant
from apps.core.models import FeatureAuditLog


@receiver(pre_save, sender=TenantFeature)
def log_feature_changes(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        old = TenantFeature.objects.get(pk=instance.pk)
    except TenantFeature.DoesNotExist:
        return

    changed_fields = {}

    for field in ["is_enabled", "rollout_percentage", "start_date", "end_date"]:
        old_val = getattr(old, field)
        new_val = getattr(instance, field)

        if old_val != new_val:
            changed_fields[field] = {
                "old": old_val,
                "new": new_val
            }

    if changed_fields:
        FeatureAuditLog.objects.create(
            tenant=instance.tenant,
            feature_name=instance.feature_name,
            action="modified",
            old_value=changed_fields,
            new_value=changed_fields
        )


# ================================
# CACHE INVALIDATION SIGNALS
# ================================

def clear_tenant_feature_cache(tenant_id, feature_code=None):
    """Utility to clear cache for a specific tenant and feature, or all features."""
    if feature_code:
        cache_key = f"tenant_feature_{tenant_id}_{feature_code}"
        cache.delete(cache_key)
    else:
        # If no code, we might need a way to clear all for this tenant
        # Since we don't track all keys, the next best thing is to wait for 5min 
        # or clear the ones we know about. 
        # For now, let's clear common ones or assume full refresh is needed.
        from apps.tenants.context_processors import ALL_FEATURE_CODES
        for code in ALL_FEATURE_CODES:
            cache.delete(f"tenant_feature_{tenant_id}_{code}")


@receiver([post_save, post_delete], sender=PlanFeature)
def invalidate_plan_feature_cache(sender, instance, **kwargs):
    """When a plan's feature changes, invalidate cache for all tenants on that plan."""
    tenants = Tenant.objects.filter(subscription__plan=instance.plan)
    for tenant in tenants:
        clear_tenant_feature_cache(tenant.id, instance.feature.code)


@receiver([post_save, post_delete], sender=TenantFeature)
def invalidate_tenant_feature_cache(sender, instance, **kwargs):
    """When a tenant-specific feature override changes, invalidate cache."""
    clear_tenant_feature_cache(instance.tenant.id, instance.feature_name)


@receiver(post_save, sender=SubscriptionPlan)
def invalidate_plan_cache(sender, instance, **kwargs):
    """If a plan status changes, invalidate all features for all associated tenants."""
    tenants = Tenant.objects.filter(subscription__plan=instance)
    for tenant in tenants:
        clear_tenant_feature_cache(tenant.id)


@receiver([post_save, post_delete], sender=TenantSubscription)
def invalidate_subscription_cache(sender, instance, **kwargs):
    """When a tenant's subscription changes (plan or status), invalidate their feature cache."""
    clear_tenant_feature_cache(instance.tenant.id)
