import uuid
from django.db import models
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
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    specialization = models.CharField(
        max_length=50, choices=SPECIALIZATION_CHOICES, default='General'
    )
    phone = models.CharField(max_length=20, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    qualification = models.CharField(max_length=255, blank=True, default='')
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"
