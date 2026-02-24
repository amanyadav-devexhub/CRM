import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditMixin


# ──────────────────────────────────────────────
# 1. Notification
# ──────────────────────────────────────────────
class Notification(models.Model):
    """
    In-app notification for a user. Supports multiple notification types
    and links to relevant actions via action_url.
    """

    class NotificationType(models.TextChoices):
        APPOINTMENT = "appointment", "Appointment"
        BILLING = "billing", "Billing"
        LAB = "lab", "Lab Result"
        SYSTEM = "system", "System"
        CAMPAIGN = "campaign", "Campaign"
        FEEDBACK = "feedback", "Feedback"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications",
    )
    type = models.CharField(
        max_length=15, choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    action_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Relative URL to navigate to when notification is clicked"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_notif_user"),
            models.Index(fields=["user", "is_read"], name="idx_notif_unread"),
        ]

    def __str__(self):
        status = "🟢" if not self.is_read else "⚪"
        return f"{status} {self.title} → {self.user}"


# ──────────────────────────────────────────────
# 2. Notification Preference
# ──────────────────────────────────────────────
class NotificationPreference(AuditMixin):
    """
    Per-user notification delivery preferences.
    Controls which channels are enabled and quiet hours.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)

    # Quiet hours — notifications are held during this window
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="e.g. 22:00")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="e.g. 07:00")

    class Meta:
        db_table = "notification_preferences"

    def __str__(self):
        return f"Prefs for {self.user}"
