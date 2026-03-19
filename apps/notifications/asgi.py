"""
ASGI config for HMS / CRM project.

Handles both:
  - HTTP  →  Django views / DRF
  - WS    →  Django Channels (real-time notifications)
"""

import os
import django
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "crm.settings")  # ← change "crm" to your project name
django.setup()

# Import AFTER django.setup() so apps are ready
from apps.notifications.channels.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    # ── Standard Django HTTP ──────────────────────────────────
    "http": get_asgi_application(),

    # ── WebSocket (real-time notifications) ───────────────────
    # AllowedHostsOriginValidator  → rejects connections from unknown origins
    # AuthMiddlewareStack          → populates scope["user"] from session/token
    # URLRouter                    → maps ws://host/ws/notifications/ → consumer
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})