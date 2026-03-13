"""
Context processor: injects tenant feature flags into every template.

Templates can use:
    {% if "patients" in enabled_features %} ... {% endif %}
    {% if "lab" not in enabled_features %} 🔒 ... {% endif %}
"""
from apps.tenants.models import Feature, BroadcastMessage


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
    Also injects `active_broadcast` if there is a matching broadcast for this tenant.
    """
    context = {
        "enabled_features": set(), 
        "all_features": ALL_FEATURE_CODES,
        "user_permissions": set(),
        "active_broadcast": None
    }
    
    # --- BROADCAST BANNER LOGIC ---
    active_broadcast = BroadcastMessage.objects.filter(is_active=True).first()
    
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return context

    # SuperAdmin logic
    if request.user.is_superuser:
        context["enabled_features"] = set(ALL_FEATURE_CODES)
        context["active_broadcast"] = active_broadcast # Superadmins see the active broadcast regardless of target
        return context

    tenant = getattr(request.user, "tenant", None)
    if not tenant:
        return context

    # Target matching for broadcasts
    if active_broadcast:
        if active_broadcast.target_type == 'ALL':
            context["active_broadcast"] = active_broadcast
        elif active_broadcast.target_type == 'CATEGORY' and tenant.category in active_broadcast.target_categories:
            context["active_broadcast"] = active_broadcast
        elif active_broadcast.target_type == 'SPECIFIC' and tenant in active_broadcast.target_tenants.all():
            context["active_broadcast"] = active_broadcast

    # Check each feature via the cached has_feature() method on Tenant
    enabled = set()
    for code in ALL_FEATURE_CODES:
        if tenant.has_feature(code):
            enabled.add(code)

    # Fetch User Permissions for Sidebar Gating
    user_permissions = set()
    if not request.user.is_superuser and getattr(request.user, "role", None):
        user_permissions = set(request.user.role.permissions.values_list("code", flat=True))

    context["enabled_features"] = enabled
    context["user_permissions"] = user_permissions
    
    return context
