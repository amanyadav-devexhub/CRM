"""
RoleRouteMiddleware — Global auth gate + role-based route protection.

Rules:
- Public routes (/, /login/, /register/, /verify-otp/, /resend-otp/, /onboarding/*,
  /admin/, /static/, /api/) are accessible without auth.
- Admin routes (/admin-dashboard/*, /categories/*, /tenants/*) require SuperAdmin.
- All other routes require authentication.
"""
from django.shortcuts import redirect


class RoleRouteMiddleware:
    """Route-level access control based on user role."""

    # Routes accessible without authentication
    PUBLIC_PREFIXES = (
        "/login/",
        "/register/",
        "/verify-otp/",
        "/resend-otp/",
        "/admin/",          # Django admin has its own auth
        "/static/",
        "/api/",
    )

    # Routes that require SuperAdmin (user.is_superuser, user.tenant is None)
    SUPERADMIN_PREFIXES = (
        "/admin-dashboard/",
        "/categories/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # 1. Root "/" — always public (landing page or redirect)
        if path == "/":
            return self.get_response(request)

        # 2. Public routes — always accessible
        if any(path.startswith(prefix) for prefix in self.PUBLIC_PREFIXES):
            return self.get_response(request)

        # 3. Onboarding — needs auth but not tenant assignment
        if path.startswith("/onboarding/"):
            if not request.user.is_authenticated:
                return redirect("/login/")
            return self.get_response(request)

        # 4. All other routes require authentication
        if not request.user.is_authenticated:
            return redirect("/login/")

        # 5. SuperAdmin-only routes
        if any(path.startswith(prefix) for prefix in self.SUPERADMIN_PREFIXES):
            if not request.user.is_superuser:
                return redirect("/dashboard/")

        return self.get_response(request)
