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
    CATEGORY_CHOICES = [
        ('CLINIC', 'Clinic'),
        ('PHARMACY', 'Pharmacy'),
        ('HOSPITAL', 'Hospital'),
        ('LAB', 'Lab'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='CLINIC')
    subdomain = models.CharField(max_length=100, unique=True)
    email = models.EmailField()
    phone = models.CharField(max_length=15)

    # Link to django_tenants Client (schema holder)
    client = models.OneToOneField(
        "tenants.Client",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="tenant_record",
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# ================================
# CLINIC SETTINGS (Org Configuration)
# ================================

class ClinicSettings(models.Model):
    """Per-tenant clinic configuration: branding, localization, working hours."""
    tenant = models.OneToOneField(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="clinic_settings",
    )

    # ── Basic Info ──
    clinic_name = models.CharField(max_length=255, blank=True)
    logo = models.ImageField(upload_to="clinic_logos/", blank=True, null=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    registration_number = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    # ── Localization ──
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")
    currency = models.CharField(max_length=10, default="INR")
    language = models.CharField(max_length=10, default="en")
    date_format = models.CharField(max_length=20, default="DD/MM/YYYY")

    # ── Working Hours ──
    # JSON example: {"mon": {"open": "09:00", "close": "18:00"}, "tue": {...}, ...}
    working_hours = models.JSONField(default=dict, blank=True)
    # JSON example: ["2026-01-26", "2026-08-15"]
    holidays = models.JSONField(default=list, blank=True)
    emergency_available = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Clinic Settings"
        verbose_name_plural = "Clinic Settings"

    def __str__(self):
        return f"Settings for {self.tenant.name}"


# ================================
# SUBSCRIPTION PLANS
# ================================

class SubscriptionPlan(models.Model):
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    description = models.TextField(blank=True)

    # ── Resource limits ──
    max_doctors = models.IntegerField(default=1)
    max_staff = models.IntegerField(default=2)
    max_patients = models.IntegerField(default=300)
    max_appointments_per_month = models.IntegerField(default=150)

    # ── Feature flags ──
    sms_enabled = models.BooleanField(default=False)
    whatsapp_enabled = models.BooleanField(default=False)
    ai_enabled = models.BooleanField(default=False)
    export_enabled = models.BooleanField(default=False)
    custom_branding = models.BooleanField(default=False)
    api_access = models.BooleanField(default=False)
    advanced_reports = models.BooleanField(default=False)
    pharmacy_addon = models.BooleanField(default=False)
    lab_addon = models.BooleanField(default=False)

    def __str__(self):
        return self.display_name or self.name


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
        return self.status in ("ACTIVE", "TRIAL") and self.end_date > timezone.now()



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
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    feature_name = models.CharField(max_length=100)

    is_enabled = models.BooleanField(default=False)
    rollout_percentage = models.IntegerField(default=100)

    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "feature_name")

    def is_time_valid(self):
        now = timezone.now()

        if self.start_date and now < self.start_date:
            return False

        if self.end_date and now > self.end_date:
            return False

        return True

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

    # 2️⃣ Tenant override (by feature_name CharField)
    override = TenantFeature.objects.filter(
        tenant=self,
        feature_name=feature_code
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

# Attach to Tenant model
Tenant.has_feature = has_feature
