import uuid
from django.db import models
from django.utils import timezone


class Appointment(models.Model):
    """A scheduled appointment at the clinic."""
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('CONFIRMED', 'Confirmed'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
    ]

    TYPE_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('WALK_IN', 'Walk-in'),
        ('TELE_CONSULT', 'Tele-consult'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE,
        related_name='appointments', null=True, blank=True,
    )
    patient_name = models.CharField(max_length=255, blank=True,
                                     help_text="Fallback if patient record not linked")
    doctor = models.ForeignKey(
        'clinical.Doctor', on_delete=models.CASCADE, related_name='appointments'
    )
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    appointment_type = models.CharField(
        max_length=20, choices=TYPE_CHOICES, default='SCHEDULED'
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default='SCHEDULED'
    )

    # ── Walk-in / Token ──
    token_number = models.IntegerField(null=True, blank=True)

    # ── Timing ──
    check_in_time = models.TimeField(null=True, blank=True)
    check_out_time = models.TimeField(null=True, blank=True)

    # ── Details ──
    notes = models.TextField(blank=True, default='')
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cancellation_reason = models.TextField(blank=True, default='')
    no_show = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['appointment_date', 'appointment_time']

    def __str__(self):
        name = self.patient.full_name if self.patient else self.patient_name
        return f"{name} → Dr. {self.doctor.name} on {self.appointment_date}"

    @property
    def display_name(self):
        """Return patient display name."""
        if self.patient:
            return self.patient.full_name
        return self.patient_name


class AppointmentConfig(models.Model):
    """Per-tenant appointment configuration."""
    tenant = models.OneToOneField(
        'tenants.Tenant', on_delete=models.CASCADE,
        related_name='appointment_config',
    )
    default_slot_duration = models.IntegerField(default=15, help_text="Minutes")
    allow_walk_ins = models.BooleanField(default=True)
    auto_confirm = models.BooleanField(default=False)
    cancellation_window_hours = models.IntegerField(default=2)
    no_show_penalty = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    reminder_hours_before = models.JSONField(
        default=list, blank=True,
        help_text='JSON list, e.g. [24, 2]'
    )
    auto_followup_days = models.IntegerField(default=7)

    def __str__(self):
        return f"Appointment Config — {self.tenant.name}"


class AppointmentActivity(models.Model):
    """Audit log for appointment lifecycle events."""
    ACTION_CHOICES = [
        ('BOOKED', 'Booked'),
        ('CONFIRMED', 'Confirmed'),
        ('DECLINED', 'Declined'),
        ('CHECKED_IN', 'Checked In'),
        ('CHECKED_OUT', 'Checked Out'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('NO_SHOW', 'No Show'),
        ('RESCHEDULED', 'Rescheduled'),
        ('STATUS_CHANGED', 'Status Changed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name='activities'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    performed_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='appointment_actions',
    )
    old_status = models.CharField(max_length=20, blank=True, default='')
    new_status = models.CharField(max_length=20, blank=True, default='')
    notes = models.TextField(blank=True, default='')
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['performed_at']
        verbose_name_plural = 'Appointment Activities'

    def __str__(self):
        user = self.performed_by.email if self.performed_by else 'System'
        return f"{self.get_action_display()} by {user} at {self.performed_at}"
