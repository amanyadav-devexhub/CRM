from django.views.generic import TemplateView
from .models import Notification


class NotificationCenterView(TemplateView):
    """In-app notification center — shows all notifications for the current user."""
    template_name = "notifications/center.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            notifications = Notification.objects.filter(user=self.request.user)
        else:
            notifications = Notification.objects.all()

        # Filter by type
        notif_type = self.request.GET.get("type")
        if notif_type:
            notifications = notifications.filter(type=notif_type)

        # Filter by read status
        is_read = self.request.GET.get("is_read")
        if is_read is not None:
            notifications = notifications.filter(is_read=is_read.lower() == "true")

        ctx["notifications"] = notifications[:50]
        ctx["total_count"] = notifications.count()
        ctx["unread_count"] = notifications.filter(is_read=False).count()
        ctx["type_filter"] = notif_type or ""
        ctx["types"] = Notification.NotificationType.choices
        return ctx
