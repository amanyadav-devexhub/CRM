from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.billing.models import ServiceCatalog
from apps.tenants.models import SubscriptionPlan
from apps.billing.services.stripe_service import StripeService

@receiver(post_save, sender=ServiceCatalog)
def sync_service_to_stripe(sender, instance, created, **kwargs):
    """Syncs ServiceCatalog item to Stripe on create or update."""
    # To avoid recursion and unnecessary API calls on every small change,
    # we sync only if price depends on it or it's new.
    # In a production app, we'd use a background task.
    
    if not instance.stripe_price_id:
        StripeService.sync_catalog_item(instance)
    else:
        # Just update status (Active/Inactive)
        StripeService.update_stripe_status(instance)

@receiver(post_save, sender=SubscriptionPlan)
def sync_plan_to_stripe(sender, instance, created, **kwargs):
    """Syncs SubscriptionPlan to Stripe on create or update."""
    if not instance.stripe_price_id:
        StripeService.sync_catalog_item(instance)
    else:
        # Just update status
        StripeService.update_stripe_status(instance)
