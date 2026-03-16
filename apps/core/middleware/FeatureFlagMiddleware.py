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
    # Standalone routes
    "/patients/":                "patients",
    "/pharmacy/":                "pharmacy",
    "/lab/":                     "lab",
    "/communications/":          "communications",
    "/notifications/":           "notifications",

    # Dashboard sub-routes
    "/dashboard/appointments/":  "appointments",
    "/dashboard/billing/":       "billing",
    "/dashboard/clinical/":      "clinical_notes",
    "/dashboard/analytics/":     "analytics",

    # API routes
    "/api/patients/":            "patients",
    "/api/communications/":      "communications",
    "/api/notifications/":       "notifications",
}

# Paths that are exempt from feature checks
EXEMPT_PREFIXES = (
    "/login/", "/register/", "/verify-otp/", "/resend-otp/",
    "/logout/", "/admin/", "/admin-dashboard/",
    "/onboarding/", "/static/", "/categories/",
    "/tenants/",
    "/api/tenants/", "/api/auth/",
    # Safe dashboard paths (no feature gating needed)
    "/dashboard/settings/",
    "/dashboard/staff/",
    "/dashboard/doctors/",
    "/dashboard/schedules/",
)

# Exact paths that are exempt (dashboard home pages)
EXEMPT_EXACT = (
    "/", "/dashboard", "/dashboard/doctor", "/dashboard/reception",
)


class FeatureFlagMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        path = request.path
        
        # Strip trailing slash for exact matching to avoid /dashboard vs /dashboard/ issues
        clean_path = path.rstrip("/") if path != "/" else "/"

        # 1. Skip exact exempt paths (dashboard home, root, etc.)
        if clean_path in EXEMPT_EXACT:
            return None

        # 2. Skip exempt prefixes
        for prefix in EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return None

        # 3. Check view-level required_feature attribute
        feature_code = getattr(view_func, "required_feature", None)

        # 4. Fallback: URL prefix mapping
        if not feature_code:
            if path.startswith("/dashboard/inventory/"):
                type_code = request.GET.get("type_code")
                if type_code == "MEDICINE":
                    feature_code = "pharmacy"
                elif type_code == "LAB_REAGENT":
                    feature_code = "lab"
                else:
                    feature_code = "pharmacy_or_lab"
            else:
                for prefix, code in URL_FEATURE_MAP.items():
                    if path.startswith(prefix):
                        feature_code = code
                        break

        # No feature requirement found — allow
        if not feature_code:
            return None

        # 5. Must have authenticated user with a tenant
        if not request.user.is_authenticated:
            return None  # RoleRouteMiddleware handles auth redirects

        # SuperAdmins bypass feature checks
        if request.user.is_superuser:
            return None

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return None  # No tenant = onboarding user, let them through

        # 6. Check feature access
        if feature_code == "pharmacy_or_lab":
            if not (tenant.has_feature("pharmacy") or tenant.has_feature("lab")):
                return render(request, "feature_locked.html", status=403)
        elif not tenant.has_feature(feature_code):
            return render(request, "feature_locked.html", status=403)

        return None

