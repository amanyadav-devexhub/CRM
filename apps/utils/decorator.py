from functools import wraps
from django.http import HttpResponseForbidden

def feature_required(feature_code):
    def decorator(view_func):

        @wraps(view_func)
        def _wrapped(request, *args, **kwargs):

            tenant = getattr(request, "tenant", None)

            if not tenant:
                return HttpResponseForbidden("Tenant not found")

            if not tenant.has_feature(feature_code):
                return HttpResponseForbidden(
                    "Upgrade your subscription to access this feature."
                )

            return view_func(request, *args, **kwargs)

        return _wrapped
    return decorator
