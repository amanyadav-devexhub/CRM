from django.db import models
from django.conf import settings
import uuid

class LabTest(models.Model):
    """Catalog of available laboratory tests."""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100, blank=True)
    reference_range = models.CharField(max_length=200, blank=True)
    sample_type = models.CharField(max_length=100, blank=True, help_text="e.g., Blood, Urine")
    preparation_instructions = models.TextField(blank=True, help_text="e.g., Fasting for 12 hours")
    turnaround_time = models.CharField(max_length=100, blank=True, help_text="e.g., 24 hours")
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class LabTestParameter(models.Model):
    """Specific parameter for a multi-parameter lab test (e.g., RBC for CBC)."""
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE, related_name='parameters')
    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=50, blank=True)
    normal_low = models.CharField(max_length=100, blank=True)
    normal_high = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return f"{self.test.name} - {self.name}"

class LabTestPackage(models.Model):
    """A bundle of tests sold together."""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tests = models.ManyToManyField(LabTest, related_name='packages')
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class LabOrder(models.Model):
    """A request for one or more lab tests for a patient."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('COLLECTED', 'Sample Collected'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('VERIFIED', 'Verified'),
        ('REPORT_UPLOADED', 'Report Uploaded'),
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
    technician = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_lab_orders')
    appointment = models.ForeignKey('appointments.Appointment', on_delete=models.SET_NULL, null=True, blank=True, related_name='lab_orders')
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
    collection_location = models.CharField(max_length=200, blank=True)
    collected_at = models.DateTimeField(null=True, blank=True)
    collected_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='collected_samples')
    barcode = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def __str__(self):
        return f"{self.sample_type} for {self.order.id}"

class LabResult(models.Model):
    """Recorded result for a specific test (or parameter) within a lab order."""
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='results')
    test = models.ForeignKey(LabTest, on_delete=models.CASCADE)
    parameter = models.ForeignKey(LabTestParameter, on_delete=models.CASCADE, null=True, blank=True, related_name='results')
    value = models.CharField(max_length=200)
    unit = models.CharField(max_length=50, blank=True)
    is_abnormal = models.BooleanField(default=False)
    pdf_report = models.FileField(upload_to='lab_reports/', null=True, blank=True)
    recorded_at = models.DateTimeField(auto_now_add=True)
    recorded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='recorded_results')
    verified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='verified_results')
    verified_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.test.name} Result for {self.order.patient}"

class LabInventoryItem(models.Model):
    """Laboratory inventory items such as reagents, consumables, etc."""
    CATEGORY_CHOICES = [
        ('REAGENT', 'Reagent'),
        ('CONSUMABLE', 'Consumable'),
        ('EQUIPMENT', 'Equipment / Part'),
        ('OTHER', 'Other'),
    ]
    
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True, help_text="Stock Keeping Unit / Barcode")
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='REAGENT')
    unit = models.CharField(max_length=50, help_text="e.g., kits, boxes, ml")
    quantity_in_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10.00, help_text="Alert when stock falls below this level")
    expiry_date = models.DateField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.quantity_in_stock} {self.unit})"

class LabInventoryTransaction(models.Model):
    """Tracking stock additions, consumption, or adjustments."""
    TRANSACTION_TYPES = [
        ('ADD', 'Stock Added (Purchase)'),
        ('CONSUME', 'Stock Consumed (Usage)'),
        ('ADJUST', 'Manual Adjustment (Correction/Damage)'),
    ]

    item = models.ForeignKey(LabInventoryItem, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, help_text="Amount added or consumed")
    date = models.DateTimeField(auto_now_add=True)
    performed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='inventory_transactions')
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_transaction_type_display()} - {self.item.name} ({self.quantity})"

class LabOrderAuditLog(models.Model):
    """Tracks all result modifications, approval chains, and status changes for compliance."""
    order = models.ForeignKey(LabOrder, on_delete=models.CASCADE, related_name='audit_logs')
    action = models.CharField(max_length=255) # e.g., "Result Modified", "Verified", "Sample Collected"
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    details = models.TextField(blank=True) # JSON or text details of what changed

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.order.id} - {self.action} by {self.user}"
