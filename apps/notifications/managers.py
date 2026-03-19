"""
Notification Manager - Central service for creating and sending notifications
"""
from typing import List, Dict, Any, Optional
from django.contrib.auth import get_user_model
from apps.notifications.models import Notification
from apps.notifications.channels import (
    InAppChannel, EmailChannel, SMSChannel, WhatsAppChannel
)
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class NotificationManager:
    """
    Central manager for creating and dispatching notifications across all channels.
    
    Usage:
        NotificationManager.send(
            user=patient_user,
            notification_type="appointment_confirmation",
            title="Appointment Confirmed",
            body="Your appointment is confirmed for tomorrow at 10 AM",
            channels=["inapp", "email", "sms"],
            priority="high",
            action_url="/appointments/123/",
            metadata={"appointment_id": "123"}
        )
    """
    
    CHANNEL_MAP = {
        'inapp': InAppChannel,
        'email': EmailChannel,
        'sms': SMSChannel,
        'whatsapp': WhatsAppChannel,
    }
    
    @classmethod
    def send(
        cls,
        user: User,
        notification_type: str,
        title: str,
        body: str,
        channels: List[str] = None,
        priority: str = "medium",
        action_url: str = None,
        action_text: str = None,
        image_url: str = None,
        metadata: Dict[str, Any] = None,
        send_async: bool = True,
    ) -> Notification:
        """
        Create and send a notification across specified channels.
        
        Args:
            user: User to send notification to
            notification_type: Type of notification (e.g., "appointment_confirmation")
            title: Notification title
            body: Notification message
            channels: List of channels to send through (default: ["inapp"])
            priority: Priority level - "low", "medium", "high", "urgent"
            action_url: Optional URL for action button
            action_text: Optional text for action button
            image_url: Optional image URL
            metadata: Optional JSON metadata
            send_async: If True, send via Celery. If False, send immediately.
        
        Returns:
            Notification instance
        """
        if channels is None:
            channels = ["inapp"]
        
        # Create in-app notification record
        notification = Notification.objects.create(
            user=user,
            tenant=getattr(user, 'tenant', None),
            type=notification_type,
            title=title,
            body=body,
            priority=priority,
            action_url=action_url,
            action_text=action_text,
            image_url=image_url,
            metadata=metadata or {},
        )
        
        # Send through requested channels
        if send_async:
            from apps.notifications.tasks import send_notification_task
            send_notification_task.delay(notification.id, channels)
        else:
            cls._send_through_channels(notification, channels)
        
        return notification
    
    @classmethod
    def _send_through_channels(cls, notification: Notification, channels: List[str]):
        """Send notification through specified channels immediately."""
        for channel_name in channels:
            channel_class = cls.CHANNEL_MAP.get(channel_name)
            if not channel_class:
                logger.warning(f"Unknown channel: {channel_name}")
                continue
            
            try:
                channel = channel_class()
                channel.send(notification)
                logger.info(f"Sent notification {notification.id} via {channel_name}")
            except Exception as e:
                logger.error(f"Failed to send via {channel_name}: {e}")
    
    @classmethod
    def send_bulk(
        cls,
        users: List[User],
        notification_type: str,
        title: str,
        body: str,
        channels: List[str] = None,
        **kwargs
    ) -> List[Notification]:
        """Send same notification to multiple users."""
        notifications = []
        for user in users:
            notif = cls.send(
                user=user,
                notification_type=notification_type,
                title=title,
                body=body,
                channels=channels,
                **kwargs
            )
            notifications.append(notif)
        return notifications
    
    @classmethod
    def mark_as_read(cls, notification_id: int, user: User) -> bool:
        """Mark a notification as read."""
        try:
            notification = Notification.objects.get(id=notification_id, user=user)
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @classmethod
    def mark_all_as_read(cls, user: User) -> int:
        """Mark all notifications as read for a user."""
        count = Notification.objects.filter(user=user, is_read=False).update(is_read=True)
        return count
    
    @classmethod
    def get_unread_count(cls, user: User) -> int:
        """Get unread notification count for a user."""
        return Notification.objects.filter(user=user, is_read=False, is_archived=False).count()


# Convenience functions
def notify(user, notification_type, title, body, **kwargs):
    """Shorthand for NotificationManager.send()"""
    return NotificationManager.send(user, notification_type, title, body, **kwargs)


def notify_bulk(users, notification_type, title, body, **kwargs):
    """Shorthand for NotificationManager.send_bulk()"""
    return NotificationManager.send_bulk(users, notification_type, title, body, **kwargs)