import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditMixin, SoftDeleteMixin


# ──────────────────────────────────────────────
# 1. Message Template
# ──────────────────────────────────────────────
class MessageTemplate(AuditMixin):
    """
    Reusable message templates for WhatsApp, SMS, and email channels.
    Supports variable placeholders like {{patient_name}}, {{date}}.
    """

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, help_text="Internal template name")
    channel = models.CharField(max_length=10, choices=Channel.choices)
    subject = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Subject line (email only)"
    )
    body = models.TextField(help_text="Message body with {{variable}} placeholders")
    variables = models.JSONField(
        default=list, blank=True,
        help_text='List of variable names, e.g. ["patient_name", "date", "doctor"]'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "message_templates"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.get_channel_display()})"


# ──────────────────────────────────────────────
# 2. Message
# ──────────────────────────────────────────────
class Message(AuditMixin):
    """
    A single message sent to a patient via any channel.
    Can be linked to a template or composed directly.
    """

    class Channel(models.TextChoices):
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"
        EMAIL = "email", "Email"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        READ = "read", "Read"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE,
        related_name="messages",
    )
    template = models.ForeignKey(
        MessageTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="messages",
    )
    channel = models.CharField(max_length=10, choices=Channel.choices)
    subject = models.CharField(max_length=255, blank=True, default="")
    body = models.TextField()
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.QUEUED
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, default="")
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="sent_messages",
    )

    class Meta:
        db_table = "messages"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"], name="idx_message_status"),
            models.Index(fields=["channel"], name="idx_message_channel"),
            models.Index(fields=["patient", "-created_at"], name="idx_message_patient"),
        ]

    def __str__(self):
        return f"{self.get_channel_display()} → {self.patient} ({self.status})"


# ──────────────────────────────────────────────
# 3. Campaign
# ──────────────────────────────────────────────
class Campaign(AuditMixin, SoftDeleteMixin):
    """
    Broadcast campaign for health alerts, offers, or follow-up reminders.
    Uses segment_filter to target specific patient groups.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    template = models.ForeignKey(
        MessageTemplate, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="campaigns",
    )
    segment_filter = models.JSONField(
        default=dict, blank=True,
        help_text='Patient filter criteria, e.g. {"tags": ["VIP"], "gender": "F"}'
    )
    scheduled_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.DRAFT
    )
    total_recipients = models.PositiveIntegerField(default=0)
    sent_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="campaigns",
    )

    class Meta:
        db_table = "campaigns"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"

    @property
    def delivery_rate(self):
        if self.total_recipients == 0:
            return 0
        return round((self.sent_count / self.total_recipients) * 100, 1)


# ──────────────────────────────────────────────
# 4. Feedback
# ──────────────────────────────────────────────
class Feedback(AuditMixin):
    """
    Patient feedback and rating, optionally linked to an appointment.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        "patients.Patient", on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    appointment = models.ForeignKey(
        "appointments.Appointment", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="feedbacks",
    )
    rating = models.PositiveSmallIntegerField(
        help_text="Rating from 1 (poor) to 5 (excellent)"
    )
    comments = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "patient_feedback"
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.patient} — {self.rating}★"


# ──────────────────────────────────────────────
# 5. Automation Rule
# ──────────────────────────────────────────────
class AutomationRule(AuditMixin):
    """
    Rules for automatically sending messages triggered by events
    (e.g., Appointment booked, 24h before appointment, 2 days after).
    """
    class TriggerEvent(models.TextChoices):
        APPOINTMENT_BOOKED = "apt_booked", "Appointment Booked"
        APPOINTMENT_REMINDER = "apt_reminder", "Appointment Reminder"
        APPOINTMENT_FOLLOWUP = "apt_followup", "Appointment Follow-up"
        PAYMENT_RECEIVED = "payment_recv", "Payment Received"
        WELCOME_MESSAGE = "welcome", "Welcome Message (New Patient)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    trigger_event = models.CharField(max_length=20, choices=TriggerEvent.choices)
    
    # E.g. -24 (24 hours before), 0 (immediate), 48 (48 hours after)
    offset_hours = models.IntegerField(
        default=0, help_text="Hours before (negative) or after (positive) the event"
    )
    
    template = models.ForeignKey(
        MessageTemplate, on_delete=models.CASCADE, related_name="automation_rules"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "automation_rules"

    def __str__(self):
        return f"{self.name} ({self.get_trigger_event_display()})"
