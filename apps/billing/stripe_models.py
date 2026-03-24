import uuid
from django.db import models
from django.conf import settings

class StripeCustomer(models.Model):
    """Maps a Django user/tenant to a Stripe Customer ID."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="stripe_customer",
        null=True, blank=True
    )
    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="stripe_customer",
        null=True, blank=True
    )
    stripe_customer_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        owner = self.user or self.tenant
        return f"{owner} -> {self.stripe_customer_id}"

class StripeProductMapping(models.Model):
    """Maps a SubscriptionPlan or ServiceCatalog item to a Stripe Product."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Can be linked to either a collective SubscriptionPlan or an individual ServiceCatalog item
    content_type = models.CharField(max_length=50, choices=[
        ('PLAN', 'Subscription Plan'),
        ('SERVICE', 'Service Catalog Item')
    ])
    object_id = models.UUIDField() # ID of the Plan or Service
    
    stripe_product_id = models.CharField(max_length=100, unique=True)
    stripe_price_id = models.CharField(max_length=100, unique=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('content_type', 'object_id')

    def __str__(self):
        return f"{self.content_type} ({self.object_id}) -> {self.stripe_product_id}"
