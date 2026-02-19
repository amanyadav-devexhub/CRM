from datetime import date
from django.db import models
from django.conf import settings

class UsageMetric(models.Model):
    tenant = models.ForeignKey("tenants.Tenant", on_delete=models.CASCADE)
    metric_type = models.CharField(max_length=100)
    quantity = models.IntegerField(default=0)
    month = models.DateField()

    class Meta:
        unique_together = ("tenant", "metric_type", "month")
