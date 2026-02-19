from django.core.cache import cache
from apps.core.models import ABTest


class ABService:

    @staticmethod
    def get_variant(user_id, feature_name):

        cache_key = f"ab:{user_id}:{feature_name}"
        variant = cache.get(cache_key)

        if variant:
            return variant

        try:
            test = ABTest.objects.get(
                feature_name=feature_name,
                active=True
            )
        except ABTest.DoesNotExist:
            return None

        bucket = hash(str(user_id)) % 100

        if bucket < test.traffic_split:
            variant = test.variant_a
        else:
            variant = test.variant_b

        cache.set(cache_key, variant, 86400)

        return variant
