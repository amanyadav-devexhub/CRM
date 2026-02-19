from django.http import HttpResponseForbidden

class FeatureFlagMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):

        feature_code = getattr(view_func, "required_feature", None)

        if not feature_code:
            return None

        tenant = getattr(request, "tenant", None)

        if not tenant:
            return HttpResponseForbidden("Tenant not found.")

        if not tenant.has_feature(feature_code):
            return HttpResponseForbidden(
                "Feature not available in your subscription."
            )

        return None
