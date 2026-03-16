from django import template

register = template.Library()

@register.filter(name='has_permission')
def has_permission(user, permission_code):
    """
    Checks if a user has a specific permission via their assigned role.
    Usage in templates:
    {% if request.user|has_permission:'prescriptions.issue' %}
        <button>Write Prescription</button>
    {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
        
    try:
        return user.has_permission(permission_code)
    except AttributeError:
        # Fallback if user model doesn't have the method
        return False

@register.filter(name='has_any_permission')
def has_any_permission(user, permission_codes_string):
    """
    Checks if a user has ANY of the given permissions via their assigned role.
    Usage in templates:
    {% if request.user|has_any_permission:'patients.view_records,patients.register' %}
        <a href="...">Patients</a>
    {% endif %}
    """
    if not user or not user.is_authenticated:
        return False
        
    codes = [code.strip() for code in permission_codes_string.split(',')]
    
    try:
        return any(user.has_permission(code) for code in codes)
    except AttributeError:
        return False
