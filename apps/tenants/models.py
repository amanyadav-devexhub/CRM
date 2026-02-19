from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
import uuid 
from django.utils import timezone


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    paid_until = models.DateField(null=True, blank=True)
    on_trial = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)

    auto_create_schema = True  # VERY IMPORTANT

    def __str__(self):
        return self.name


class Domain(DomainMixin):
    pass

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    subdomain = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
    
class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ('BASIC', 'Basic'),
        ('PRO', 'Pro'),
        ('ENTERPRISE', 'Enterprise'),
    ]

    name = models.CharField(max_length=50, choices=PLAN_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    max_doctors = models.IntegerField()
    ai_enabled = models.BooleanField(default=False)


class TenantSubscription(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('EXPIRED', 'Expired'),
        ('CANCELLED', 'Cancelled'),
        ('TRIAL', 'Trial'),
        ('SUSPENDED', 'Suspended'),
    ]

    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="subscription",
        blank=True     # TEMPORARY
    )

    plan = models.ForeignKey(
        "tenants.SubscriptionPlan",
        on_delete=models.PROTECT
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    start_date = models.DateTimeField(default=timezone.now)
    end_date = models.DateTimeField()

    trial = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def is_active(self):
        return self.status == "ACTIVE" and self.end_date > timezone.now()



# ================================
# FEATURE TOGGLE SYSTEM
# ================================

class Feature(models.Model):
    """
    Master feature registry (platform-level features)
    """
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Global kill switch
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# Attach features directly to SubscriptionPlan
SubscriptionPlan.add_to_class(
    "features",
    models.ManyToManyField("Feature", blank=True)
)


class TenantFeature(models.Model):
    """
    Tenant-level feature override
    """
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="feature_overrides"
    )

    feature = models.ForeignKey(
        Feature,
        on_delete=models.CASCADE
    )

    is_enabled = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tenant", "feature")

    def __str__(self):
        return f"{self.tenant.name} - {self.feature.code}"


from django.core.cache import cache

def has_feature(self, feature_code):
    """
    Central feature checking logic
    """
    cache_key = f"tenant_feature_{self.id}_{feature_code}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    # 1️⃣ Check subscription
    subscription = getattr(self, "subscription", None)

    if not subscription or not subscription.is_active():
        return False

    try:
        feature = Feature.objects.get(code=feature_code, is_active=True)
    except Feature.DoesNotExist:
        return False

    # 2️⃣ Tenant override
    override = TenantFeature.objects.filter(
        tenant=self,
        feature=feature
    ).first()

    if override:
        result = override.is_enabled
    else:
        # 3️⃣ Plan default
        result = subscription.plan.features.filter(
            id=feature.id
        ).exists()

    cache.set(cache_key, result, 300)  # cache 5 min
    return result
