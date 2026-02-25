"""
RoleRouteMiddleware — Global auth gate + role-based route protection.

Rules:
- Public routes (/, /login/, /register/, /verify-otp/, /resend-otp/, /onboarding/*,
  /admin/, /static/, /api/) are accessible without auth.
- Admin routes (/admin-dashboard/*, /categories/*, /tenants/*) require SuperAdmin.
- Auth pages (login, register, verify-otp, etc.) on tenant subdomains are
  redirected to the public domain so sessions/auth work correctly.
- All other routes require authentication.
"""
from django.shortcuts import redirect
from django.conf import settings


class RoleRouteMiddleware:
    """Route-level access control based on user role."""

    # Routes accessible without authentication
    PUBLIC_PREFIXES = (
        "/login/",
        "/register/",
        "/verify-otp/",
        "/resend-otp/",
        "/password-reset/",
        "/admin/",          # Django admin has its own auth
        "/static/",
        "/api/",
    )

    # Auth pages that MUST live on the public domain (not tenant subdomains)
    AUTH_PREFIXES = (
        "/login/",
        "/register/",
        "/verify-otp/",
        "/resend-otp/",
        "/password-reset/",
        "/onboarding/",
    )

    # Routes that require SuperAdmin (user.is_superuser, user.tenant is None)
    SUPERADMIN_PREFIXES = (
        "/admin-dashboard/",
        "/admin-tenants/",
        "/admin-subscriptions/",
        "/admin-plans/",
        "/admin-features/",
        "/admin-settings/",
        "/admin-analytics/",
        "/admin-revenue/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def _get_public_url(self, path):
        """Build URL on the public domain (no tenant subdomain)."""
        port = getattr(settings, "TENANT_PORT", "8000")
        scheme = "https" if getattr(settings, "TENANT_USE_HTTPS", False) else "http"
        return f"{scheme}://localhost:{port}{path}"

    def _is_tenant_subdomain(self, request):
        """Check if the request is on a tenant subdomain (not plain localhost)."""
        host = request.get_host().split(":")[0]  # strip port
        return host != "localhost" and host.endswith(".localhost")

    def __call__(self, request):
        path = request.path
        on_tenant = self._is_tenant_subdomain(request)

        # 1. If on a tenant subdomain and accessing auth pages, redirect to public domain
        if on_tenant and any(path.startswith(p) for p in self.AUTH_PREFIXES):
            return redirect(self._get_public_url(path))

        # 2. Root "/" — always public (landing page or redirect)
        if path == "/":
            return self.get_response(request)

        # 3. Public routes — always accessible
        if any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES):
            return self.get_response(request)

        # 4. Onboarding — needs auth but not tenant assignment
        if path.startswith("/onboarding/"):
            if not request.user.is_authenticated:
                return redirect(self._get_public_url("/login/"))
            return self.get_response(request)

        # 5. All other routes require authentication
        if not request.user.is_authenticated:
            # Redirect to public domain login (not relative, so cookies work)
            return redirect(self._get_public_url("/login/"))

        # 6. SuperAdmin-only routes
        if any(path.startswith(prefix) for prefix in self.SUPERADMIN_PREFIXES):
            if not request.user.is_superuser:
                return redirect("/dashboard/")

        return self.get_response(request)

