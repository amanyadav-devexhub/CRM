from django.db import models
from django.conf import settings
import uuid


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
        'clinical.Doctor', on_delete=models.CASCADE, related_name='clinical_notes'
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
        'clinical.Doctor', on_delete=models.CASCADE, related_name='prescriptions'
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
