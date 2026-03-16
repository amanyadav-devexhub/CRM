"""
FeatureFlagMiddleware — Enforces feature access at the URL level.

Two enforcement strategies:
1. View-level: checks `view_func.required_feature` attribute
2. URL-prefix: maps URL prefixes to feature codes (fallback)

Both use Tenant.has_feature() which is cached for 5 minutes.
"""
from django.http import HttpResponseForbidden
from django.shortcuts import render


# ──────────────────────────────────────────────
# URL prefix → feature code mapping
# ──────────────────────────────────────────────
URL_FEATURE_MAP = {
    "/patients/":       "patients",
    "/appointments/":   "appointments",
    "/billing/":        "billing",
    "/pharmacy/":       "pharmacy",
    "/labs/":           "lab",
    "/communications/": "communications",
    "/notifications/":  "notifications",
    "/analytics/":      "analytics",
}

# Paths that are exempt from feature checks
EXEMPT_PREFIXES = (
    "/", "/login/", "/register/", "/verify-otp/", "/resend-otp/",
    "/logout/", "/admin/", "/admin-dashboard/", "/dashboard/",
    "/onboarding/", "/static/", "/api/", "/categories/",
    "/tenants/",
)


class FeatureFlagMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path

        # 1. Skip exempt paths
        if path in ("/", ""):
            return None
        for prefix in EXEMPT_PREFIXES:
            if prefix != "/" and path.startswith(prefix):
                return None

        # 2. Check view-level required_feature attribute
        feature_code = getattr(view_func, "required_feature", None)

        # 3. Fallback: URL prefix mapping
        if not feature_code:
            for prefix, code in URL_FEATURE_MAP.items():
                if path.startswith(prefix):
                    feature_code = code
                    break

        # No feature requirement found — allow
        if not feature_code:
            return None

        # 4. Must have authenticated user with a tenant
        if not request.user.is_authenticated:
            return None  # RoleRouteMiddleware handles auth redirects

        # SuperAdmins bypass feature checks
        if request.user.is_superuser:
            return None

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return None  # No tenant = onboarding user, let them through

        # 5. Check feature access
        if not tenant.has_feature(feature_code):
            return render(request, "feature_locked.html", status=403)

        return None
