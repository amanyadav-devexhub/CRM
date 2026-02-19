from django.db import models
from django.conf import settings

class FeatureAuditLog(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    feature_name = models.CharField(max_length=100)
    action = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL
    )
    old_value = models.JSONField(null=True, blank=True)
    new_value = models.JSONField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]


class ABTest(models.Model):
    name = models.CharField(max_length=100)
    feature_name = models.CharField(max_length=100)
    traffic_split = models.IntegerField(default=50)
    active = models.BooleanField(default=True)

    variant_a = models.JSONField()
    variant_b = models.JSONField()
