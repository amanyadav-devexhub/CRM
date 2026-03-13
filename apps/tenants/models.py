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


# ================================
# DYNAMIC CATEGORIES
# ================================

class Category(models.Model):
    """Dynamic healthcare service categories that can be managed from the admin panel."""
    ICON_CHOICES = [
        ('local_hospital', 'Hospital/Clinic'),
        ('medication', 'Medication/Pharmacy'),
        ('apartment', 'Building/Hospital'),
        ('biotech', 'Lab/Biotech'),
        ('healing', 'Healing'),
        ('psychology', 'Psychology'),
        ('elderly', 'Elderly Care'),
        ('child_care', 'Child Care'),
        ('medical_services', 'Medical Services'),
        ('health_and_safety', 'Health & Safety'),
        ('vaccines', 'Vaccines'),
        ('monitor_heart', 'Cardiology'),
        ('visibility', 'Eye Care'),
        ('dentistry', 'Dentistry'),
        ('spa', 'Wellness/Spa'),
        ('fitness_center', 'Fitness'),
        ('bloodtype', 'Blood Bank'),
        ('emergency', 'Emergency'),
        ('science', 'Research'),
        ('category', 'General'),
    ]

    COLOR_CHOICES = [
        ('green', 'Green'),
        ('blue', 'Blue'),
        ('purple', 'Purple'),
        ('orange', 'Orange'),
        ('cyan', 'Cyan'),
        ('red', 'Red'),
        ('pink', 'Pink'),
    ]

    code = models.CharField(max_length=30, unique=True, help_text="Uppercase code like CLINIC, PHARMACY")
    name = models.CharField(max_length=100, help_text="Display name, e.g. 'Clinics'")
    description = models.TextField(blank=True, help_text="Short description for the category card")
    icon = models.CharField(max_length=50, choices=ICON_CHOICES, default='category')
    color = models.CharField(max_length=20, choices=COLOR_CHOICES, default='blue')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0, help_text="Lower number = shown first")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'name']
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name

    @property
    def tenant_count(self):
        return self.tenants.count()


class Tenant(models.Model):
    CATEGORY_CHOICES = [
        ('CLINIC', 'Clinic'),
        ('PHARMACY', 'Pharmacy'),
        ('HOSPITAL', 'Hospital'),
        ('LAB', 'Lab'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='CLINIC')
    category_obj = models.ForeignKey(
        'tenants.Category',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='tenants',
    )
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


class CategoryRoleTemplate(models.Model):
    category = models.ForeignKey(
        'tenants.Category', 
        on_delete=models.CASCADE, 
        related_name="role_templates"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, blank=True, default='',
        help_text="Unique identifier for this role within the category (e.g. doctor, receptionist)")
    description = models.TextField(blank=True, null=True)
    permissions = models.ManyToManyField('accounts.Permission', blank=True)
    is_admin_role = models.BooleanField(
        default=False, 
        help_text="Should the onboarding user receive this role?"
    )
    is_active = models.BooleanField(default=True, help_text="Is this role currently active?")

    class Meta:
        unique_together = ('category', 'name')
        ordering = ['category', '-is_admin_role', 'name']

    def __str__(self):
        return f"{self.name} ({self.category.name})"


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
    category = models.ForeignKey(
        "tenants.Category",
        on_delete=models.CASCADE,
        related_name="plans",
        null=True, blank=True # Allow null temporarily for existing plans during migration
    )
    name = models.CharField(max_length=50, unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    BILLING_CHOICES = [
        ('MONTHLY', 'Monthly'),
        ('YEARLY', 'Yearly'),
    ]
    billing_cycle = models.CharField(max_length=20, choices=BILLING_CHOICES, default='MONTHLY')
    
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0, help_text="Order in which plan appears (lowest first)")

    def __str__(self):
        cat_name = self.category.name if self.category else "Global"
        return f"{self.display_name or self.name} ({cat_name})"

    class Meta:
        ordering = ['order', 'price']


class Resource(models.Model):
    """
    Defines what can be limited across the platform.
    e.g., code=MAX_DOCTORS, name="Maximum Doctors"
    """
    code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    # Optional constraint: resource only applies to specific Category
    category = models.ForeignKey(
        "tenants.Category", on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PlanResourceLimit(models.Model):
    """
    Maps a resource limit to a specific SubscriptionPlan.
    """
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="resource_limits")
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    # -1 = unlimited, 0 = none, >0 = specific limit
    limit_value = models.IntegerField(default=-1)

    class Meta:
        unique_together = ('plan', 'resource')

    def __str__(self):
        limit_str = "Unlimited" if self.limit_value == -1 else str(self.limit_value)
        return f"{self.plan.name} - {self.resource.name}: {limit_str}"


class PlanFeature(models.Model):
    """
    Maps a boolean feature to a specific SubscriptionPlan.
    """
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name="features")
    feature = models.ForeignKey("tenants.Feature", on_delete=models.CASCADE)

    class Meta:
        unique_together = ('plan', 'feature')

    def __str__(self):
        return f"{self.plan.name} includes {self.feature.name}"


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
    category = models.ForeignKey(
        "tenants.Category", on_delete=models.SET_NULL, null=True, blank=True
    )

    # Global kill switch
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


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
    Central feature checking logic.
    Priority:
      1. Plan features are the source of truth (controlled by superadmin)
      2. TenantFeature overrides can explicitly grant/revoke a feature
    """
    cache_key = f"tenant_feature_{self.id}_{feature_code}"
    cached = cache.get(cache_key)

    if cached is not None:
        return cached

    # 1️⃣ Check subscription
    subscription = getattr(self, "subscription", None)

    if not subscription or not subscription.is_active():
        cache.set(cache_key, False, 300)
        return False

    try:
        feature = Feature.objects.get(code=feature_code, is_active=True)
    except Feature.DoesNotExist:
        cache.set(cache_key, False, 300)
        return False

    # 2️⃣ Check plan features (source of truth)
    in_plan = subscription.plan.features.filter(
        feature_id=feature.id
    ).exists()

    # 3️⃣ Check for explicit tenant override (can grant OR revoke)
    override = TenantFeature.objects.filter(
        tenant=self,
        feature_name=feature_code
    ).first()

    if override:
        # Explicit override takes precedence
        result = override.is_enabled and override.is_time_valid()
    else:
        # Fall back to plan
        result = in_plan

    cache.set(cache_key, result, 300)
    return result

# Attach to Tenant model
Tenant.has_feature = has_feature


# ================================
# SUPERADMIN BROADCASTS
# ================================

class BroadcastMessage(models.Model):
    """
    Global system broadcast message (e.g., Maintenance alerts).
    Only one message can be active at a time to show as a banner.
    """
    TARGET_CHOICES = [
        ('ALL', 'All Tenants'),
        ('CATEGORY', 'Specific Categories'),
        ('SPECIFIC', 'Specific Tenants'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subject = models.CharField(max_length=255, help_text="Short title for the banner (e.g. SYSTEM MAINTENANCE)")
    message = models.TextField(help_text="Detailed message text")
    target_type = models.CharField(max_length=20, choices=TARGET_CHOICES, default='ALL')
    
    # Targeting arrays
    target_categories = models.JSONField(default=list, blank=True, help_text="List of category codes if TARGET=CATEGORY")
    target_tenants = models.ManyToManyField(Tenant, blank=True, related_name="broadcasts", help_text="Specific tenants if TARGET=SPECIFIC")
    
    is_active = models.BooleanField(default=False, help_text="If True, this banner currently displays. Only one can be active.")
    
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="created_broadcasts"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "broadcast_messages"
        ordering = ["-created_at"]

    def __str__(self):
        status = "🟢 ACTIVE" if self.is_active else "⚫ INACTIVE"
        return f"[{status}] {self.subject}"

    def save(self, *args, **kwargs):
        # Enforce single active broadcast rule
        if self.is_active:
            BroadcastMessage.objects.exclude(id=self.id).update(is_active=False)
        super().save(*args, **kwargs)
