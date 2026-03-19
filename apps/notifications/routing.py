"""
WebSocket Routing for Notifications

Add this to your config/routing.py (or create it if it doesn't exist)
"""
from django.urls import path
from apps.notifications.consumers import NotificationConsumer

websocket_urlpatterns = [
    path('ws/notifications/', NotificationConsumer.as_asgi()),
]