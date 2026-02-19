from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.tenants.models import Tenant


# ---------------------------
# Permission Model (Global)
# ---------------------------
class Permission(models.Model):
    code = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


# ---------------------------
# Role Model (Tenant-Specific)
# ---------------------------
class Role(models.Model):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="roles"
    )
    name = models.CharField(max_length=100)
    is_system_role = models.BooleanField(default=False)

    permissions = models.ManyToManyField(
        Permission,
        related_name="roles",
        blank=True
    )

    class Meta:
        unique_together = ("tenant", "name")  # Prevent duplicate roles per tenant

    def __str__(self):
        return f"{self.name} ({self.tenant.name})"


# ---------------------------
# RolePermission Mapping
# ---------------------------
class RolePermission(models.Model):
    role = models.ForeignKey(
        Role,
        on_delete=models.CASCADE,
        related_name="role_permissions"
    )
    permission = models.ForeignKey(
        Permission,
        on_delete=models.CASCADE
    )

    class Meta:
        unique_together = ("role", "permission")


# ---------------------------
# Custom User Model
# ---------------------------
class User(AbstractUser):
    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name="users"
    )
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users"
    )

    def has_permission(self, permission_code):
        if not self.role:
            return False

        return self.role.permissions.filter(
            code=permission_code
        ).exists()

    def __str__(self):
        return f"{self.username} ({self.tenant.name})"
