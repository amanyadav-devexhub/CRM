from django.contrib import admin
from .models import Role, Permission, RolePermission, User


# -----------------------
# Permission Admin
# -----------------------
@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ("code", "name")
    search_fields = ("code", "name")


# -----------------------
# Role Admin
# -----------------------
@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "is_system_role")
    list_filter = ("tenant",)
    search_fields = ("name",)
    filter_horizontal = ("permissions",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        # Super admin sees all
        if request.user.is_superuser:
            return qs

        # Tenant admin sees only their tenant roles
        return qs.filter(tenant=request.user.tenant)


# -----------------------
# User Admin
# -----------------------
@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("username", "email", "tenant", "role")
    list_filter = ("tenant", "role")
    search_fields = ("username", "email")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        return qs.filter(tenant=request.user.tenant)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):

        if db_field.name == "role" and not request.user.is_superuser:
            kwargs["queryset"] = Role.objects.filter(
                tenant=request.user.tenant
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
