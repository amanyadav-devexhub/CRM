import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone


class Doctor(models.Model):
    """A doctor/physician at the clinic."""
    SPECIALIZATION_CHOICES = [
        ('General', 'General Practice'),
        ('Cardiology', 'Cardiology'),
        ('Dermatology', 'Dermatology'),
        ('Orthopedics', 'Orthopedics'),
        ('Pediatrics', 'Pediatrics'),
        ('ENT', 'ENT'),
        ('Neurology', 'Neurology'),
        ('Ophthalmology', 'Ophthalmology'),
        ('Gynecology', 'Gynecology'),
        ('Psychiatry', 'Psychiatry'),
        ('Dentistry', 'Dentistry'),
        ('Physiotherapy', 'Physiotherapy'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="doctor_profile",
        help_text="Link to a user account for login",
    )
    name = models.CharField(max_length=255)
    specialization = models.CharField(
        max_length=50, choices=SPECIALIZATION_CHOICES, default='General'
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    qualification = models.CharField(max_length=255, blank=True, default='')

    # ── Fees & Revenue ──
    consultation_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    follow_up_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    commission_pct = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        help_text="Commission percentage (0–100)"
    )

    # ── Capabilities ──
    tele_consult_enabled = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"


class DoctorSlot(models.Model):
    """Available time slots for a doctor. One row per day-of-week."""
    DAY_CHOICES = [
        (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday'),
        (3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name="slots"
    )
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    slot_duration = models.IntegerField(default=15, help_text="Minutes per slot")
    max_bookings = models.IntegerField(default=1, help_text="Max patients per slot")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['day_of_week', 'start_time']
        unique_together = ('doctor', 'day_of_week', 'start_time')

    def __str__(self):
        return f"Dr. {self.doctor.name} — {self.get_day_of_week_display()} {self.start_time}–{self.end_time}"


class ClinicalNote(models.Model):
    """SOAP notes for a patient consultation."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='clinical_notes'
    )
    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='clinical_notes'
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='clinical_notes'
    )

    # ── SOAP Format ──
    subjective = models.TextField(blank=True, help_text="Patient's chief complaints and history")
    objective = models.TextField(blank=True, help_text="Vitals, physical exam findings, lab results")
    assessment = models.TextField(blank=True, help_text="Diagnosis and medical impression")
    plan = models.TextField(blank=True, help_text="Treatment plan, medications, follow-up")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.patient.full_name} on {self.created_at.strftime('%Y-%m-%d')}"


class Prescription(models.Model):
    """A medical prescription given to a patient."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(
        'patients.Patient', on_delete=models.CASCADE, related_name='prescriptions'
    )
    appointment = models.ForeignKey(
        'appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='prescriptions'
    )
    doctor = models.ForeignKey(
        Doctor, on_delete=models.CASCADE, related_name='prescriptions'
    )
    notes = models.TextField(blank=True, help_text="General instructions")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Prescription for {self.patient.full_name} on {self.created_at.strftime('%Y-%m-%d')}"


class PrescriptionItem(models.Model):
    """Individual medicine inside a prescription."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prescription = models.ForeignKey(
        Prescription, on_delete=models.CASCADE, related_name='items'
    )
    medicine_name = models.CharField(max_length=255)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg, 1 tablet")
    frequency = models.CharField(max_length=100, help_text="e.g., Twice a day (1-0-1)")
    duration = models.CharField(max_length=100, help_text="e.g., 5 days")
    instructions = models.TextField(blank=True, help_text="e.g., After food")

    def __str__(self):
        return f"{self.medicine_name} - {self.dosage}"
