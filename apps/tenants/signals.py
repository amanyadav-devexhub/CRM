from django.db.models.signals import pre_save
from django.dispatch import receiver
from apps.tenants.models import TenantFeature
from apps.core.models import FeatureAuditLog


@receiver(pre_save, sender=TenantFeature)
def log_feature_changes(sender, instance, **kwargs):
    if not instance.pk:
        return

    old = TenantFeature.objects.get(pk=instance.pk)

    changed_fields = {}

    for field in ["is_enabled", "rollout_percentage", "start_date", "end_date"]:
        old_val = getattr(old, field)
        new_val = getattr(instance, field)

        if old_val != new_val:
            changed_fields[field] = {
                "old": old_val,
                "new": new_val
            }

    if changed_fields:
        FeatureAuditLog.objects.create(
            tenant=instance.tenant,
            feature_name=instance.feature_name,
            action="modified",
            old_value=changed_fields,
            new_value=changed_fields
        )
