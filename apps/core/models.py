import uuid
from django.db import models
from django.utils import timezone


class AuditMixin(models.Model):
    """
    Abstract mixin that adds automatic created_at / updated_at timestamps.
    Inherit this in every tenant-scoped model.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteManager(models.Manager):
    """Default manager that excludes soft-deleted records."""

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class AllObjectsManager(models.Manager):
    """Manager that returns ALL records, including soft-deleted ones."""
    pass


class SoftDeleteMixin(models.Model):
    """
    Abstract mixin for soft-delete behaviour.
    - Calling .delete() sets is_deleted=True instead of removing the row.
    - Default manager filters out deleted records automatically.
    - Use .all_objects to query including deleted records.
    - Use .hard_delete() to permanently remove a record.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        """Soft delete – mark as deleted instead of removing."""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        """Permanently delete the record from the database."""
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        """Restore a soft-deleted record."""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=["is_deleted", "deleted_at"])
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
