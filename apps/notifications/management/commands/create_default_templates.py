import logging
from django.utils import timezone
from django.template import Template, Context
from django.conf import settings
from .models import (
    Notification, NotificationQueue, NotificationTemplate,
    NotificationPreference, NotificationLog, UserDevice
)

logger = logging.getLogger(__name__)

def send_notification(user, notification_type, title, body, 
                     channel_priority=None, metadata=None, 
                     action_url=None, tenant=None):
    """
    Main function to send notifications through multiple channels
    
    Args:
        user: User object (recipient)
        notification_type: 'appointment', 'billing', 'lab', etc.
        title: Notification title
        body: Notification body
        channel_priority: ['in_app', 'email', 'sms', 'whatsapp', 'push']
        metadata: Dict of additional data
        action_url: URL to navigate when clicked
        tenant: Tenant object (if not provided, uses user.tenant)
    """
    if not tenant:
        tenant = user.tenant
    
    # Default channel priority
    if not channel_priority:
        channel_priority = ['in_app', 'email', 'sms', 'whatsapp']
    
    # Get user preferences
    try:
        prefs = NotificationPreference.objects.get(user=user)
    except NotificationPreference.DoesNotExist:
        prefs = None
    
    results = []
    
    # 1. ALWAYS create in-app notification (stored in DB)
    in_app_notification = None
    if 'in_app' in channel_priority and (not prefs or prefs.in_app_enabled):
        in_app_notification = Notification.objects.create(
            user=user,
            tenant=tenant,
            type=notification_type,
            title=title,
            body=body,
            action_url=action_url,
            metadata=metadata or {}
        )
        results.append({'channel': 'in_app', 'success': True, 'id': in_app_notification.id})
    
    # 2. Send to other channels via queue
    for channel in channel_priority:
        if channel == 'in_app':
            continue
            
        # Check if channel is enabled in preferences
        if prefs:
            if channel == 'email' and not prefs.email_enabled:
                continue
            if channel == 'sms' and not prefs.sms_enabled:
                continue
            if channel == 'whatsapp' and not prefs.whatsapp_enabled:
                continue
            if channel == 'push' and not prefs.push_enabled:
                continue
        
        # Get template for this channel
        template = NotificationTemplate.objects.filter(
            tenant=tenant,
            name=notification_type,
            channel=channel,
            is_active=True
        ).first()
        
        if not template:
            # Try global template
            template = NotificationTemplate.objects.filter(
                tenant__isnull=True,
                name=notification_type,
                channel=channel,
                is_active=True
            ).first()
        
        if not template:
            logger.warning(f"No template found for {notification_type} - {channel}")
            continue
        
        # Render template with metadata
        rendered_body = render_template(template.body, metadata or {})
        rendered_subject = render_template(template.subject, metadata or {}) if template.subject else title
        
        # Create queue entry
        queue_item = NotificationQueue.objects.create(
            tenant=tenant,
            user=user,
            in_app_notification=in_app_notification,
            template=template,
            channel=channel,
            subject=rendered_subject,
            body=rendered_body,
            recipient_email=user.email if channel in ['email'] else None,
            recipient_phone=getattr(user, 'phone', None) if channel in ['sms', 'whatsapp'] else None,
            metadata=metadata or {},
            status='pending',
            scheduled_for=timezone.now()
        )
        
        results.append({'channel': channel, 'success': True, 'queue_id': queue_item.id})
        
        # Log creation
        NotificationLog.objects.create(
            tenant=tenant,
            user=user,
            queue_item=queue_item,
            event_type='created',
            channel=channel
        )
    
    return results


def render_template(template_text, context_dict):
    """Render a template string with context"""
    if not template_text:
        return ""
    try:
        template = Template(template_text)
        context = Context(context_dict)
        return template.render(context)
    except Exception as e:
        logger.error(f"Template rendering error: {e}")
        return template_text


def send_appointment_reminder(appointment):
    """Helper function for appointment reminders"""
    patient = appointment.patient
    tenant = appointment.tenant
    
    metadata = {
        'patient_name': patient.get_full_name(),
        'doctor_name': appointment.doctor.get_full_name(),
        'date': appointment.date.strftime('%B %d, %Y'),
        'time': appointment.time.strftime('%I:%M %p'),
        'clinic_name': tenant.name,
        'appointment_id': str(appointment.id)
    }
    
    return send_notification(
        user=patient,
        notification_type='appointment_reminder',
        title='Appointment Reminder',
        body=f"Reminder: You have an appointment with Dr. {appointment.doctor.get_full_name()} tomorrow at {appointment.time.strftime('%I:%M %p')}",
        channel_priority=['whatsapp', 'sms', 'email', 'in_app'],
        metadata=metadata,
        action_url=f"/appointments/{appointment.id}",
        tenant=tenant
    )


def send_lab_results_ready(lab_result):
    """Helper function for lab results"""
    patient = lab_result.patient
    tenant = lab_result.tenant
    
    metadata = {
        'patient_name': patient.get_full_name(),
        'test_name': lab_result.test_name,
        'test_date': lab_result.test_date.strftime('%B %d, %Y'),
        'results_link': f"{settings.BASE_URL}/lab/results/{lab_result.id}",
        'clinic_name': tenant.name
    }
    
    return send_notification(
        user=patient,
        notification_type='lab_results',
        title='Lab Results Ready',
        body=f"Your lab results for {lab_result.test_name} are now available.",
        channel_priority=['email', 'whatsapp', 'in_app'],
        metadata=metadata,
        action_url=f"/lab/results/{lab_result.id}",
        tenant=tenant
    )


def mark_notification_as_read(notification_id, user):
    """Mark a notification as read"""
    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        
        NotificationLog.objects.create(
            tenant=user.tenant,
            user=user,
            notification=notification,
            event_type='read',
            channel='in_app'
        )
        return True
    except Notification.DoesNotExist:
        return False


def get_unread_count(user):
    """Get unread notification count for user"""
    return Notification.objects.filter(user=user, is_read=False).count()