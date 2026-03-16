from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect

class HasTenantPermissionMixin(AccessMixin):
    """
    Verify that the current user has the required permission 
    inside their current Tenant's RBAC Role.
    """
    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
            
        # Superusers bypass checks
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)
            
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/login/")
            
        if self.required_permission:
            # required_permission can be a single string or a list/tuple of strings
            perms_to_check = self.required_permission
            if isinstance(perms_to_check, str):
                perms_to_check = [perms_to_check]
                
            has_access = any(request.user.has_permission(p) for p in perms_to_check)
            
            if not has_access:
                return self.handle_no_permission()
                
        return super().dispatch(request, *args, **kwargs)
