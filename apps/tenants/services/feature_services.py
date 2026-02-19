from django.core.cache import cache
from tenants.models import TenantFeature, Feature

CACHE_TIMEOUT = 60 * 5  # 5 minutes


def is_feature_enabled(tenant, feature_code):
    cache_key = f"tenant_feature_{tenant.id}_{feature_code}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    try:
        feature = Feature.objects.get(code=feature_code, is_active=True)
    except Feature.DoesNotExist:
        return False

    # 1️⃣ Tenant override
    override = TenantFeature.objects.filter(
        tenant=tenant, feature=feature
    ).first()

    if override:
        result = override.is_enabled
    else:
        # 2️⃣ Fallback to subscription plan
        result = tenant.subscription_plan.features.filter(
            id=feature.id
        ).exists()

    cache.set(cache_key, result, CACHE_TIMEOUT)
    return result
