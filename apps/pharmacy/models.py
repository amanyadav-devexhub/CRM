from django.db import models
from django.utils import timezone
import uuid


class Medicine(models.Model):
    """Pharmacy inventory item."""
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('EXPIRED', 'Expired'),
    ]
    CATEGORY_CHOICES = [
        ('Analgesic', 'Analgesic'),
        ('Antibiotic', 'Antibiotic'),
        ('Antihistamine', 'Antihistamine'),
        ('Supplement', 'Supplement'),
        ('Antacid', 'Antacid'),
        ('Antiviral', 'Antiviral'),
        ('General', 'General'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    sku = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    batch_number = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock = models.PositiveIntegerField(default=0)
    expiry_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_STOCK')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def save(self, *args, **kwargs):
        # Auto-set status based on stock & expiry
        if self.expiry_date and self.expiry_date < timezone.now().date():
            self.status = 'EXPIRED'
        elif self.stock == 0:
            self.status = 'OUT_OF_STOCK'
        elif self.stock <= 20:
            self.status = 'LOW_STOCK'
        else:
            self.status = 'IN_STOCK'
        super().save(*args, **kwargs)


class Sale(models.Model):
    """A completed pharmacy sale/transaction."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(max_length=50, unique=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Invoice {self.invoice_number}"


class SaleItem(models.Model):
    """Line item within a sale."""
    sale = models.ForeignKey(Sale, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"


class Prescription(models.Model):
    """A prescription record for pharmacy verification."""
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
