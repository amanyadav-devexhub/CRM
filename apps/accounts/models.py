from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid
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
        unique_together = ("tenant", "name")

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
        null=True,
        blank=True,
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
        if self.tenant:
            return f"{self.username} ({self.tenant.name})"
        return f"{self.username} (Platform Admin)"


# ---------------------------
# Employee Model
# ---------------------------
class Employee(models.Model):
    """Employee profile linked to a User account."""
    EMPLOYEE_TYPES = [
        ('DOCTOR', 'Doctor'),
        ('RECEPTIONIST', 'Receptionist'),
        ('NURSE', 'Nurse'),
        ('LAB_ASSISTANT', 'Lab Assistant'),
        ('ACCOUNTANT', 'Accountant'),
        ('CUSTOM', 'Custom'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="employee_profile",
    )
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPES)
    department = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    joining_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} ({self.get_employee_type_display()})"
