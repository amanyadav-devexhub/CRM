import string
import secrets
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def generate_secure_password(length=12):
    """Generate a secure random password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        password = ''.join(secrets.choice(alphabet) for i in range(length))
        if (any(c.islower() for c in password)
                and any(c.isupper() for c in password)
                and sum(c.isdigit() for c in password) >= 3):
            break
    return password

def send_staff_welcome_email(user, raw_password, request):
    """
    Send welcome email to newly created staff with their credentials.
    The login URL points to the public domain.
    """
    subject = "Welcome to the Clinic Portal - Your Login Credentials"
    
    # In production, this should be the public domain (e.g., app.yourdomain.com)
    # For local dev, we construct it based on the request host.
    host = request.get_host()
    
    # We strip the tenant subdomain to make sure they log in via the public domain
    # Assuming local dev resembles: clinic.localhost:8000 -> localhost:8000
    if "localhost" in host or "127.0.0.1" in host:
        public_domain = "localhost:8000" if "localhost" in host else "127.0.0.1:8000"
    else:
        # Example: testclinic.platform.com -> platform.com
        parts = host.split('.')
        if len(parts) > 2:
            public_domain = '.'.join(parts[1:])
        else:
            public_domain = host
            
    protocol = "https" if request.is_secure() else "http"
    login_url = f"{protocol}://{public_domain}/login/"
    
    context = {
        'user': user,
        'raw_password': raw_password,
        'login_url': login_url,
        'clinic_name': user.tenant.name if user.tenant else "Our Clinic",
    }
    
    html_message = f"""
    <h2>Welcome, {user.get_full_name() or user.username}!</h2>
    <p>You have been invited to join the staff portal for <b>{context['clinic_name']}</b>.</p>
    <p>Here are your secure login credentials:</p>
    <ul>
        <li><b>Email:</b> {user.email}</li>
        <li><b>Password:</b> {raw_password}</li>
    </ul>
    <p>Please log in at the following link:</p>
    <p><a href="{login_url}">{login_url}</a></p>
    <br>
    <p><i>We highly recommend changing your password after your first login.</i></p>
    """
    
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_message,
        fail_silently=True,  # Set to False in production for debugging
    )

def provision_category_roles(tenant):
    """
    Auto-provisions predefined roles based on the tenant's category.
    Reads from the CategoryRoleTemplate database models to generate
    custom roles dynamically.
    """
    from apps.accounts.models import Role
    from apps.tenants.models import CategoryRoleTemplate
    
    # Get the templates for this tenant's category
    if not tenant.category:
        return
        
    templates = CategoryRoleTemplate.objects.filter(category=tenant.category)
    
    for template in templates:
        role, created = Role.objects.get_or_create(
            tenant=tenant,
            name=template.name,
            defaults={
                "is_system_role": True,
                "source_template": template,
            }
        )
        
        # If it already existed but had no template link, set it now
        if not created and not role.source_template:
            role.source_template = template
            role.save(update_fields=["source_template"])

        # Map permissions from the template
        role.permissions.set(template.permissions.all())
