from django.http import HttpResponseForbidden

def permission_required(permission_code):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):

            if not request.user.is_authenticated:
                return HttpResponseForbidden("Authentication required")

            # Tenant isolation check
            if request.user.tenant != request.tenant:
                return HttpResponseForbidden("Invalid tenant access")

            if not request.user.has_permission(permission_code):
                return HttpResponseForbidden("Permission denied")

            return view_func(request, *args, **kwargs)

        return wrapper
    return decorator
