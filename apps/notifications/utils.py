# apps/notifications/utils.py

from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from .models import Notification, NotificationPreference
import logging
import json

logger = logging.getLogger(__name__)
User = get_user_model()

# ========== Functions for NotificationViewSet ==========

def mark_notification_as_read(notification_id, user):
    """
    Mark a notification as read
    
    Args:
        notification_id: ID of the notification
        user: User object making the request
    
    Returns:
        bool: True if successful
    """
    try:
        notification = Notification.objects.get(id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        logger.info(f"Notification {notification_id} marked as read for user {user.id}")
        return True
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found for user {user.id}")
        return False
    except Exception as e:
        logger.error(f"Error marking notification as read: {str(e)}")
        return False

def get_unread_count(user):
    """
    Get count of unread notifications for a user
    
    Args:
        user: User object
    
    Returns:
        int: Number of unread notifications
    """
    try:
        return Notification.objects.filter(
            user=user,
            is_read=False
        ).count()
    except Exception as e:
        logger.error(f"Error getting unread count: {str(e)}")
        return 0


# ========== Function for sending notifications (matches your view's call pattern) ==========

def send_notification(user, notification_type, title, body, channel_priority=None, metadata=None, action_url=None, tenant=None):
    """
    Send a notification to a user
    
    Args:
        user: User object
        notification_type: Type of notification
        title: Notification title
        body: Notification body content
        channel_priority: List of channels in priority order ['whatsapp', 'sms', 'email', 'in_app']
        metadata: Additional data dictionary
        action_url: URL to navigate when notification is clicked
        tenant: Tenant object for multi-tenant setup
    
    Returns:
        Notification object
    """
    try:
        # Create the notification in database
        notification = Notification.objects.create(
            user=user,
            notification_type=notification_type,
            title=title,
            body=body,
            metadata=metadata or {},
            action_url=action_url,
            tenant=tenant,
            is_read=False,
            created_at=timezone.now()
        )
        
        # Get user's notification preferences
        try:
            prefs = NotificationPreference.objects.get(user=user)
        except NotificationPreference.DoesNotExist:
            prefs = None
        
        # Determine which channels to use
        channels = channel_priority or ['in_app']  # Default to in-app only
        
        # Send through each channel based on preferences
        for channel in channels:
            if channel == 'email' and prefs and prefs.email_enabled:
                send_email_notification(user.email, title, body, metadata)
            elif channel == 'sms' and prefs and prefs.sms_enabled:
                send_sms_notification(user.phone, body)  # You'll need to implement this
            elif channel == 'whatsapp' and prefs and prefs.whatsapp_enabled:
                send_whatsapp_notification(user.phone, body)  # You'll need to implement this
            elif channel == 'in_app':
                # Already created above
                pass
        
        logger.info(f"Notification sent to user {user.id}: {title}")
        return notification
        
    except Exception as e:
        logger.error(f"Error sending notification: {str(e)}")
        return None

def send_email_notification(email, title, body, metadata=None):
    """Send email notification"""
    try:
        html_body = f"""
        <h2>{title}</h2>
        <p>{body}</p>
        """
        if metadata:
            html_body += "<h3>Additional Details:</h3><ul>"
            for key, value in metadata.items():
                html_body += f"<li><strong>{key}:</strong> {value}</li>"
            html_body += "</ul>"
        
        send_mail(
            subject=title,
            message=body,
            html_message=html_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=True,
        )
        logger.info(f"Email sent to {email}")
    except Exception as e:
        logger.error(f"Email failed: {str(e)}")

def send_sms_notification(phone, message):
    """Send SMS notification - implement with your SMS provider"""
    # TODO: Implement SMS sending (Twilio, etc.)
    logger.info(f"SMS would be sent to {phone}: {message}")
    pass

def send_whatsapp_notification(phone, message):
    """Send WhatsApp notification - implement with WhatsApp Business API"""
    # TODO: Implement WhatsApp messaging
    logger.info(f"WhatsApp message would be sent to {phone}: {message}")
    pass


# ========== Additional utility functions ==========

def get_user_notifications(user, limit=50, unread_only=False):
    """Get notifications for a user"""
    queryset = Notification.objects.filter(user=user)
    
    if unread_only:
        queryset = queryset.filter(is_read=False)
    
    return queryset.order_by('-created_at')[:limit]

def mark_all_as_read(user):
    """Mark all notifications as read for a user"""
    return Notification.objects.filter(
        user=user,
        is_read=False
    ).update(is_read=True)

def delete_old_notifications(days=30):
    """Delete notifications older than specified days"""
    cutoff_date = timezone.now() - timezone.timedelta(days=days)
    deleted_count = Notification.objects.filter(
        created_at__lt=cutoff_date,
        is_read=True  # Only delete read notifications
    ).delete()[0]
    logger.info(f"Deleted {deleted_count} old notifications")
    return deleted_count