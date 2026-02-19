import random
from django.core.cache import cache
from apps.tenants.models import TenantFeature


class FeatureFlagService:

    @staticmethod
    def is_active(tenant, feature_name, user_id=None):

        cache_key = f"feature:{tenant.id}:{feature_name}"
        feature = cache.get(cache_key)

        if not feature:
            try:
                feature = TenantFeature.objects.get(
                    tenant=tenant,
                    feature_name=feature_name
                )
                cache.set(cache_key, feature, 300)
            except TenantFeature.DoesNotExist:
                return False

        if not feature.is_enabled:
            return False

        if not feature.is_time_valid():
            return False

        # Percentage rollout
        if user_id:
            bucket = hash(str(user_id)) % 100
            return bucket < feature.rollout_percentage

        return True
