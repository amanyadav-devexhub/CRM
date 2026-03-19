"""
WebSocket Consumer for Real-Time Notifications
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import logging

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time notifications.
    
    Frontend connection:
        const ws = new WebSocket('ws://localhost:8000/ws/notifications/');
    """
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope["user"]
        
        # Only allow authenticated users
        if not self.user.is_authenticated:
            await self.close()
            return
        
        # Join user's notification group
        self.user_id = self.user.id
        self.group_name = f"notifications_{self.user_id}"
        
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"✅ WebSocket connected: User {self.user_id}")
        
        # Send current unread count on connect
        unread_count = await self.get_unread_count()
        await self.send(text_data=json.dumps({
            'type': 'unread_count',
            'count': unread_count
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        logger.info(f"❌ WebSocket disconnected: User {self.user_id}")
    
    async def receive(self, text_data):
        """Handle messages from WebSocket client."""
        try:
            data = json.loads(text_data)
            action = data.get('action')
            
            if action == 'mark_read':
                # Mark notification as read
                notification_id = data.get('notification_id')
                success = await self.mark_notification_read(notification_id)
                
                if success:
                    unread_count = await self.get_unread_count()
                    await self.send(text_data=json.dumps({
                        'type': 'marked_read',
                        'notification_id': notification_id,
                        'unread_count': unread_count
                    }))
            
            elif action == 'mark_all_read':
                # Mark all notifications as read
                count = await self.mark_all_read()
                await self.send(text_data=json.dumps({
                    'type': 'marked_all_read',
                    'count': count
                }))
            
            elif action == 'get_notifications':
                # Fetch recent notifications
                notifications = await self.get_recent_notifications()
                await self.send(text_data=json.dumps({
                    'type': 'notifications_list',
                    'notifications': notifications
                }))
                
        except json.JSONDecodeError:
            logger.error("Invalid JSON received from WebSocket")
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
    
    async def notification_message(self, event):
        """
        Handle notification messages sent to this user's group.
        This is called by InAppChannel when a new notification is created.
        """
        notification = event['notification']
        
        # Send to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'new_notification',
            'notification': notification
        }))
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Database Queries (sync -> async)
    # ═══════════════════════════════════════════════════════════════════════════
    
    @database_sync_to_async
    def get_unread_count(self):
        """Get unread notification count for current user."""
        from apps.notifications.models import Notification
        return Notification.objects.filter(
            user_id=self.user_id,
            is_read=False,
            is_archived=False
        ).count()
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        """Mark a notification as read."""
        from apps.notifications.models import Notification
        try:
            notification = Notification.objects.get(
                id=notification_id,
                user_id=self.user_id
            )
            notification.is_read = True
            notification.save(update_fields=['is_read'])
            return True
        except Notification.DoesNotExist:
            return False
    
    @database_sync_to_async
    def mark_all_read(self):
        """Mark all notifications as read."""
        from apps.notifications.models import Notification
        count = Notification.objects.filter(
            user_id=self.user_id,
            is_read=False
        ).update(is_read=True)
        return count
    
    @database_sync_to_async
    def get_recent_notifications(self, limit=20):
        """Get recent notifications for user."""
        from apps.notifications.models import Notification
        notifications = Notification.objects.filter(
            user_id=self.user_id,
            is_archived=False
        ).order_by('-created_at')[:limit]
        
        return [
            {
                'id': n.id,
                'type': n.type,
                'title': n.title,
                'body': n.body,
                'priority': n.priority,
                'is_read': n.is_read,
                'action_url': n.action_url,
                'action_text': n.action_text,
                'image_url': n.image_url,
                'created_at': n.created_at.isoformat(),
            }
            for n in notifications
        ]