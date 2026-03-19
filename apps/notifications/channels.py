"""
Notification Channels - Handlers for different delivery methods
"""
from abc import ABC, abstractmethod
from typing import Any
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# BASE CHANNEL
# ═══════════════════════════════════════════════════════════════════════════════

class BaseChannel(ABC):
    """Base class for all notification channels."""
    
    @abstractmethod
    def send(self, notification):
        """Send notification through this channel."""
        pass
    
    def log_success(self, notification, channel_name):
        """Log successful delivery."""
        logger.info(f"✅ Sent {channel_name} notification {notification.id} to {notification.user.email}")
    
    def log_failure(self, notification, channel_name, error):
        """Log failed delivery."""
        logger.error(f"❌ Failed {channel_name} notification {notification.id}: {error}")


# ═══════════════════════════════════════════════════════════════════════════════
# IN-APP CHANNEL (WebSocket)
# ═══════════════════════════════════════════════════════════════════════════════

class InAppChannel(BaseChannel):
    """In-app notifications via WebSocket."""
    
    def send(self, notification):
        """Send notification via WebSocket to connected clients."""
        try:
            channel_layer = get_channel_layer()
            user_id = notification.user.id
            
            # Send to user's notification group
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user_id}",
                {
                    "type": "notification_message",
                    "notification": {
                        "id": notification.id,
                        "type": notification.type,
                        "title": notification.title,
                        "body": notification.body,
                        "priority": notification.priority,
                        "action_url": notification.action_url,
                        "action_text": notification.action_text,
                        "image_url": notification.image_url,
                        "created_at": notification.created_at.isoformat(),
                        "is_read": notification.is_read,
                    }
                }
            )
            self.log_success(notification, "WebSocket")
        except Exception as e:
            self.log_failure(notification, "WebSocket", e)


# ═══════════════════════════════════════════════════════════════════════════════
# EMAIL CHANNEL
# ═══════════════════════════════════════════════════════════════════════════════

class EmailChannel(BaseChannel):
    """Email notifications via SMTP."""
    
    def send(self, notification):
        """Send email notification."""
        try:
            user = notification.user
            
            # Render email template (you can create custom templates per type)
            html_message = self._render_email_template(notification)
            
            send_mail(
                subject=notification.title,
                message=notification.body,  # Plain text fallback
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            self.log_success(notification, "Email")
        except Exception as e:
            self.log_failure(notification, "Email", e)
    
    def _render_email_template(self, notification):
        """Render HTML email template."""
        # You can create different templates for different notification types
        template_map = {
            'appointment_confirmation': 'emails/appointment_confirmation.html',
            'payment_received': 'emails/payment_received.html',
            'lab_results_ready': 'emails/lab_results.html',
            # Add more mappings
        }
        
        template_name = template_map.get(
            notification.type,
            'emails/generic_notification.html'  # Default template
        )
        
        try:
            return render_to_string(template_name, {
                'notification': notification,
                'user': notification.user,
                'action_url': notification.action_url,
                'action_text': notification.action_text or 'View Details',
            })
        except Exception:
            # Fallback to simple HTML
            return f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>{notification.title}</h2>
                    <p>{notification.body}</p>
                    {f'<a href="{notification.action_url}" style="background: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">{notification.action_text or "View Details"}</a>' if notification.action_url else ''}
                </body>
            </html>
            """


# ═══════════════════════════════════════════════════════════════════════════════
# SMS CHANNEL (Twilio)
# ═══════════════════════════════════════════════════════════════════════════════

class SMSChannel(BaseChannel):
    """SMS notifications via Twilio."""
    
    def send(self, notification):
        """Send SMS notification."""
        try:
            user = notification.user
            phone = getattr(user, 'phone', None)
            
            if not phone:
                logger.warning(f"User {user.id} has no phone number")
                return
            
            # Check if Twilio is configured
            twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            twilio_from = getattr(settings, 'TWILIO_PHONE_NUMBER', None)
            
            if not all([twilio_sid, twilio_token, twilio_from]):
                logger.warning("Twilio not configured - skipping SMS")
                return
            
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            
            # Truncate message to SMS limits (160 chars)
            message_body = f"{notification.title}: {notification.body}"
            if len(message_body) > 160:
                message_body = message_body[:157] + "..."
            
            message = client.messages.create(
                body=message_body,
                from_=twilio_from,
                to=phone
            )
            
            self.log_success(notification, "SMS")
            
        except ImportError:
            logger.error("Twilio library not installed. Run: pip install twilio")
        except Exception as e:
            self.log_failure(notification, "SMS", e)


# ═══════════════════════════════════════════════════════════════════════════════
# WHATSAPP CHANNEL (Twilio)
# ═══════════════════════════════════════════════════════════════════════════════

class WhatsAppChannel(BaseChannel):
    """WhatsApp notifications via Twilio."""
    
    def send(self, notification):
        """Send WhatsApp notification."""
        try:
            user = notification.user
            phone = getattr(user, 'phone', None)
            
            if not phone:
                logger.warning(f"User {user.id} has no phone number")
                return
            
            # Check if Twilio is configured
            twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', None)
            twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', None)
            twilio_whatsapp = getattr(settings, 'TWILIO_WHATSAPP_NUMBER', None)
            
            if not all([twilio_sid, twilio_token, twilio_whatsapp]):
                logger.warning("Twilio WhatsApp not configured - skipping")
                return
            
            from twilio.rest import Client
            client = Client(twilio_sid, twilio_token)
            
            # Format phone number for WhatsApp
            to_whatsapp = f"whatsapp:{phone}"
            from_whatsapp = f"whatsapp:{twilio_whatsapp}"
            
            message = client.messages.create(
                body=f"*{notification.title}*\n\n{notification.body}",
                from_=from_whatsapp,
                to=to_whatsapp
            )
            
            self.log_success(notification, "WhatsApp")
            
        except ImportError:
            logger.error("Twilio library not installed. Run: pip install twilio")
        except Exception as e:
            self.log_failure(notification, "WhatsApp", e)


# ═══════════════════════════════════════════════════════════════════════════════
# EXPORT ALL CHANNELS
# ═══════════════════════════════════════════════════════════════════════════════

__all__ = [
    'BaseChannel',
    'InAppChannel',
    'EmailChannel',
    'SMSChannel',
    'WhatsAppChannel',
]