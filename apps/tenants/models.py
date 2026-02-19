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
        related_name="subscription"
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
