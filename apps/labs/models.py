from django.db import models
from django.conf import settings
import uuid

class LabTest(models.Model):
    """Catalog of available laboratory tests."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class LabOrder(models.Model):
    """A request for one or more lab tests for a patient."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COLLECTED', 'Sample Collected'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
    ]
    PRIORITY_CHOICES = [
        ('ROUTINE', 'Routine'),
        ('URGENT', 'Urgent'),
        ('STAT', 'STAT'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey('patients.Patient', on_delete=models.CASCADE, related_name='lab_orders')
    doctor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ordered_labs')
    tests = models.ManyToManyField(LabTest, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='ROUTINE')
    notes = models.TextField(blank=True)
    ordered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.id} - {self.patient}"

class LabSample(models.Model):
    """Tracking for a specific sample collected for a lab order."""
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='samples')
    sample_type = models.CharField(max_length=100) # e.g., Blood, Urine
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='collected_samples')
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.sample_type} for {self.order.id}"

class LabResult(models.Model):
    """Recorded result for a specific test within a lab order."""
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    value = models.CharField(max_length=200)
    unit = models.CharField(max_length=50, blank=True)
    is_abnormal = models.BooleanField(default=False)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='recorded_results')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='verified_results')
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.test.name} Result for {self.order.patient}"
