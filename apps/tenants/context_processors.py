"""
Context processor: injects tenant feature flags into every template.

Templates can use:
    {% if "patients" in enabled_features %} ... {% endif %}
    {% if "lab" not in enabled_features %} 🔒 ... {% endif %}
"""
from apps.tenants.models import Feature


# All feature codes that can appear in the sidebar
ALL_FEATURE_CODES = [
    "patients", "appointments", "billing", "staff", "reports_basic",
    "queue", "clinical_notes", "prescriptions", "lab", "pharmacy",
    "communications", "notifications",
    "analytics", "ai_notes", "ai_risk", "multi_branch",
]


def tenant_features(request):
    """
    Adds `enabled_features` (set) and `all_features` (list) to template context.
    SuperAdmins get ALL features enabled.
    Unauthenticated users get an empty set.
    """
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return {"enabled_features": set(), "all_features": ALL_FEATURE_CODES}

    # SuperAdmin sees everything
    if request.user.is_superuser:
        return {
            "enabled_features": set(ALL_FEATURE_CODES),
            "all_features": ALL_FEATURE_CODES,
        }

    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return {"enabled_features": set(), "all_features": ALL_FEATURE_CODES}

    # Check each feature via the cached has_feature() method on Tenant
    enabled = set()
    for code in ALL_FEATURE_CODES:
        if tenant.has_feature(code):
            enabled.add(code)

    # Fetch User Permissions for Sidebar Gating
    user_permissions = set()
    if not request.user.is_superuser and getattr(request.user, "role", None):
        user_permissions = set(request.user.role.permissions.values_list("code", flat=True))

    return {
        "enabled_features": enabled,
        "all_features": ALL_FEATURE_CODES,
        "user_permissions": user_permissions,
    }
