from django.db import models
from django.utils import timezone
import uuid

# Deprecated: Supplier, Medicine, PurchaseOrder, and their related models have been moved to apps.inventory.


# --- Prescriptions Integration ---

class Prescription(models.Model):
    """A prescription record for pharmacy verification. Can be linked to clinical prescription."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Review'),
        ('PROCESSING', 'Processing'),
        ('DISPENSED', 'Dispensed'),
        ('REJECTED', 'Rejected'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_name = models.CharField(max_length=255)
    patient_id_code = models.CharField(max_length=50, blank=True)
    doctor_name = models.CharField(max_length=255)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Rx: {self.patient_name} by {self.doctor_name}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.SET_NULL, null=True, blank=True, related_name='pharmacy_prescription_items')
    medicine_name = models.CharField(max_length=255, help_text="Fallback if medicine not in inventory")
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity_prescribed = models.DecimalField(max_digits=10, decimal_places=2, default=0)


# --- Sales & Billing ---

class Sale(models.Model):
    """A completed pharmacy sale/transaction."""
    PAYMENT_MODES = [
        ('CASH', 'Cash'),
        ('CARD', 'Credit/Debit Card'),
        ('UPI', 'UPI'),
        ('INSURANCE', 'Insurance'),
        ('OTHER', 'Other')
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True)
    prescription = models.ForeignKey(Prescription, on_delete=models.SET_NULL, null=True, blank=True, related_name='sales')
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODES, default='CASH')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"

class SaleItem(models.Model):
    """Line item within a sale."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey('inventory.InventoryItem', on_delete=models.PROTECT, null=True, blank=True, related_name='pharmacy_sale_items')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Could be MRP or discounted price
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.item.name} x{self.quantity}"

class SaleReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    return_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return for {self.sale.invoice_number}"
