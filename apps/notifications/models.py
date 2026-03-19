import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditMixin


# ──────────────────────────────────────────────
# 1. Notification (YOUR EXISTING MODEL - ENHANCED)
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
        PRESCRIPTION = "prescription", "Prescription"
        PAYMENT = "payment", "Payment"
        ALERT = "alert", "Alert"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notifications",
    )
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name="notifications", null=True, blank=True
    )
    type = models.CharField(
        max_length=20, choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    is_read = models.BooleanField(default=False, db_index=True)
    is_archived = models.BooleanField(default=False, db_index=True)
    priority = models.CharField(
        max_length=10, 
        choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')],
        default='medium'
    )
    action_url = models.CharField(
        max_length=500, blank=True, default="",
        help_text="Relative URL to navigate to when notification is clicked"
    )
    action_text = models.CharField(max_length=100, blank=True, default="View")
    image_url = models.URLField(blank=True, null=True, help_text="Optional image for notification")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional data")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "notifications"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_notif_user"),
            models.Index(fields=["user", "is_read"], name="idx_notif_unread"),
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["type", "-created_at"]),
        ]

    def __str__(self):
        status = "🟢" if not self.is_read else "⚪"
        return f"{status} {self.title} → {self.user}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])


# ──────────────────────────────────────────────
# 2. Notification Preference (YOUR EXISTING MODEL - ENHANCED)
# ──────────────────────────────────────────────
class NotificationPreference(AuditMixin):
    """
    Per-user notification delivery preferences.
    Controls which channels are enabled and quiet hours.
    """

    class ChannelPreference(models.TextChoices):
        IMMEDIATE = "immediate", "Immediate"
        DIGEST = "digest", "Daily Digest"
        QUIET = "quiet", "Quiet Hours Only"
        NEVER = "never", "Never"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="notification_preferences",
    )
    
    # Channel enable/disable
    email_enabled = models.BooleanField(default=True)
    email_address = models.EmailField(blank=True, null=True, help_text="Override email")
    
    sms_enabled = models.BooleanField(default=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, help_text="Override phone")
    
    whatsapp_enabled = models.BooleanField(default=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)
    
    push_enabled = models.BooleanField(default=True)
    in_app_enabled = models.BooleanField(default=True)
    
    # Per-type preferences (JSON: {"appointment": "immediate", "campaign": "digest"})
    type_preferences = models.JSONField(default=dict, blank=True)
    
    # Quiet hours — notifications are held during this window
    quiet_hours_start = models.TimeField(null=True, blank=True, help_text="e.g. 22:00")
    quiet_hours_end = models.TimeField(null=True, blank=True, help_text="e.g. 07:00")
    quiet_hours_timezone = models.CharField(max_length=50, default='UTC')
    
    # Digest settings
    digest_frequency = models.CharField(
        max_length=10,
        choices=[('daily', 'Daily'), ('weekly', 'Weekly'), ('never', 'Never')],
        default='daily'
    )
    last_digest_sent = models.DateTimeField(null=True, blank=True)
    
    # Unsubscribe token for email
    unsubscribe_token = models.UUIDField(default=uuid.uuid4, editable=False)
    unsubscribe_all = models.BooleanField(default=False)

    class Meta:
        db_table = "notification_preferences"
        indexes = [
            models.Index(fields=['user', 'unsubscribe_token']),
        ]

    def __str__(self):
        return f"Prefs for {self.user}"

    def get_preference_for_type(self, notification_type):
        """Get delivery preference for specific notification type"""
        return self.type_preferences.get(notification_type, 'immediate')


# ──────────────────────────────────────────────
# 3. Notification Template
# ──────────────────────────────────────────────
class NotificationTemplate(models.Model):
    """
    Templates for different notification types across channels.
    Supports placeholders like {{patient_name}} for dynamic content.
    """
    
    CHANNEL_CHOICES = [
        ('in_app', 'In-App'),
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('push', 'Push'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE, 
        null=True, blank=True, related_name='notification_templates'
    )
    name = models.CharField(max_length=100, db_index=True)  # e.g., 'appointment_reminder'
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    notification_type = models.CharField(
        max_length=20, choices=Notification.NotificationType.choices
    )
    subject = models.CharField(max_length=255, blank=True, help_text="For email")
    body = models.TextField(help_text="With placeholders like {{patient_name}}")
    preview = models.TextField(blank=True, help_text="Preview with sample data")
    
    # Template variables (for documentation)
    required_variables = models.JSONField(default=list, blank=True)
    optional_variables = models.JSONField(default=list, blank=True)
    
    language = models.CharField(max_length=10, default='en')
    is_active = models.BooleanField(default=True)
    
    # Tracking
    click_tracking = models.BooleanField(default=True)
    open_tracking = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='created_templates'
    )
    
    class Meta:
        db_table = "notification_templates"
        unique_together = ['tenant', 'name', 'channel', 'language']
        indexes = [
            models.Index(fields=['tenant', 'name', 'is_active']),
            models.Index(fields=['notification_type']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.channel}"


# ──────────────────────────────────────────────
# 4. Notification Queue (External Channels)
# ──────────────────────────────────────────────
class NotificationQueue(models.Model):
    """
    Queue for external notifications (email, SMS, WhatsApp, push).
    Tracks delivery status and retry attempts.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('clicked', 'Clicked'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('held', 'Held - Quiet Hours'),
    ]
    
    PRIORITY_CHOICES = [
        ('critical', 'Critical'),
        ('high', 'High'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='queued_notifications'
    )
    
    # Link to in-app notification (if created)
    in_app_notification = models.OneToOneField(
        Notification, on_delete=models.SET_NULL, 
        null=True, blank=True, related_name='queue_item'
    )
    
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL,
        null=True, blank=True
    )
    
    # Recipient details
    recipient_email = models.EmailField(blank=True, null=True)
    recipient_phone = models.CharField(max_length=20, blank=True, null=True)
    recipient_push_token = models.CharField(max_length=500, blank=True, null=True)
    
    # Message details
    channel = models.CharField(max_length=20, choices=NotificationTemplate.CHANNEL_CHOICES)
    subject = models.CharField(max_length=255, blank=True)
    body = models.TextField()
    metadata = models.JSONField(default=dict)  # Original template variables
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    retry_count = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    error_message = models.TextField(blank=True, null=True)
    
    # Provider tracking
    provider = models.CharField(max_length=50, blank=True, help_text="e.g., twilio, sendgrid")
    provider_message_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    provider_response = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    scheduled_for = models.DateTimeField(db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "notification_queue"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'status', 'scheduled_for']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['provider_message_id']),
            models.Index(fields=['status', 'scheduled_for']),
        ]
    
    def __str__(self):
        return f"{self.channel} - {self.status} - {self.user}"


# ──────────────────────────────────────────────
# 5. Notification Log (Audit Trail)
# ──────────────────────────────────────────────
class NotificationLog(models.Model):
    """
    Audit log for all notification events - HIPAA compliance.
    Immutable record of all notification activities.
    """
    
    EVENT_TYPES = [
        ('created', 'Created'),
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('clicked', 'Clicked'),
        ('failed', 'Failed'),
        ('retry', 'Retry'),
        ('fallback', 'Fallback'),
        ('cancelled', 'Cancelled'),
        ('held', 'Held'),
        ('digest_sent', 'Digest Sent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='notification_logs'
    )
    
    notification = models.ForeignKey(
        Notification, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs'
    )
    queue_item = models.ForeignKey(
        NotificationQueue, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='logs'
    )
    
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    channel = models.CharField(max_length=20, blank=True)
    
    # Details
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    # For compliance
    consent_at_time = models.BooleanField(default=True, help_text="User had consented at this time")
    
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = "notification_logs"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['notification']),
            models.Index(fields=['queue_item']),
            models.Index(fields=['event_type']),
            models.Index(fields=['user', '-created_at']),
        ]
    
    def __str__(self):
        return f"{self.event_type} - {self.created_at}"


# ──────────────────────────────────────────────
# 6. Notification Provider Configuration
# ──────────────────────────────────────────────
class NotificationProvider(models.Model):
    """
    API credentials for notification providers per tenant.
    Supports multiple providers per channel for failover.
    """
    
    PROVIDER_TYPES = [
        ('twilio_sms', 'Twilio SMS'),
        ('twilio_whatsapp', 'Twilio WhatsApp'),
        ('sendgrid', 'SendGrid'),
        ('gupshup', 'Gupshup'),
        ('firebase', 'Firebase Cloud Messaging'),
        ('onesignal', 'OneSignal'),
        ('smtp', 'Custom SMTP'),
        ('ses', 'AWS SES'),
        ('sns', 'AWS SNS'),
    ]
    
    CHANNEL_CHOICES = [
        ('sms', 'SMS'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('push', 'Push'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        'tenants.Tenant', on_delete=models.CASCADE,
        null=True, blank=True, related_name='notification_providers'
    )
    provider_type = models.CharField(max_length=50, choices=PROVIDER_TYPES)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES)
    name = models.CharField(max_length=100, help_text="Display name")
    
    # Encrypted credentials (store in environment variables, reference here)
    config = models.JSONField(
        default=dict, 
        help_text="Configuration (keys, endpoints) - store sensitive data in env vars"
    )
    
    # Priority for this channel (lower = higher priority)
    priority = models.IntegerField(default=100)
    
    # Status
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False, help_text="Use as default for tenant")
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=60)
    rate_limit_per_hour = models.IntegerField(default=1000)
    rate_limit_per_day = models.IntegerField(default=10000)
    
    # Usage stats
    messages_sent_today = models.IntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "notification_providers"
        unique_together = ['tenant', 'provider_type']
        ordering = ['priority']
        indexes = [
            models.Index(fields=['tenant', 'channel', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.channel}"


# ──────────────────────────────────────────────
# 7. User Device (for Push Notifications)
# ──────────────────────────────────────────────
class UserDevice(models.Model):
    """
    User devices for push notifications.
    Tracks multiple devices per user.
    """
    
    DEVICE_TYPES = [
        ('ios', 'iOS'),
        ('android', 'Android'),
        ('web', 'Web (PWA)'),
        ('huawei', 'Huawei'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='devices'
    )
    device_type = models.CharField(max_length=20, choices=DEVICE_TYPES)
    push_token = models.CharField(max_length=500, db_index=True)
    device_id = models.CharField(max_length=255, blank=True)
    device_name = models.CharField(max_length=255, blank=True)
    
    # Metadata
    app_version = models.CharField(max_length=50, blank=True)
    device_model = models.CharField(max_length=100, blank=True)
    os_version = models.CharField(max_length=50, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    
    # Status
    is_active = models.BooleanField(default=True)
    last_active = models.DateTimeField(auto_now=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "user_devices"
        unique_together = ['user', 'push_token']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['push_token']),
        ]
    
    def __str__(self):
        return f"{self.device_type} - {self.user}"


# ──────────────────────────────────────────────
# 8. Notification Campaign (for bulk notifications)
# ──────────────────────────────────────────────
class NotificationCampaign(models.Model):
    """
    Manage bulk notification campaigns to user segments.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Template
    template = models.ForeignKey(NotificationTemplate, on_delete=models.PROTECT)
    
    # Targeting
    user_segment = models.JSONField(default=dict, help_text="Filter criteria for users")
    include_all_users = models.BooleanField(default=False)
    
    # Schedule
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    
    # Stats
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    delivered_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)
    failed_count = models.IntegerField(default=0)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='created_campaigns'
    )
    
    class Meta:
        db_table = "notification_campaigns"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} - {self.status}"


# ──────────────────────────────────────────────
# 9. Notification Attachment (for email attachments)
# ──────────────────────────────────────────────
class NotificationAttachment(models.Model):
    """
    Attachments for notifications (primarily email).
    """
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_queue = models.ForeignKey(
        NotificationQueue, on_delete=models.CASCADE,
        related_name='attachments'
    )
    file = models.FileField(upload_to='notification_attachments/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.IntegerField(help_text="Size in bytes")
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "notification_attachments"
    
    def __str__(self):
        return self.filename