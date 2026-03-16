from django.db import models
from django.utils import timezone
import uuid

# --- Suppliers & Purchase Management ---

class Supplier(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    gst_number = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

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
    
    # Pricing & Tax
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Default selling price")
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Maximum Retail Price")
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text="GST %")
    
    # Stock details
    stock = models.PositiveIntegerField(default=0)
    min_stock_level = models.PositiveIntegerField(default=10, help_text="Low stock alert trigger")
    expiry_date = models.DateField()
    barcode = models.CharField(max_length=100, blank=True, null=True, unique=True)
    image = models.ImageField(upload_to='medicine_images/', null=True, blank=True)
    
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
        elif self.stock <= self.min_stock_level:
            self.status = 'LOW_STOCK'
        else:
            self.status = 'IN_STOCK'
        super().save(*args, **kwargs)

class PurchaseOrder(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('PENDING', 'Pending Approval'),
        ('APPROVED', 'Approved'),
        ('SENT', 'Sent to Supplier'),
        ('PARTIAL', 'Partially Received'),
        ('RECEIVED', 'Fully Received'),
        ('CANCELLED', 'Cancelled'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order_number = models.CharField(max_length=50, unique=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='purchase_orders')
    order_date = models.DateField(default=timezone.now)
    expected_delivery = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DRAFT')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PO {self.order_number} - {self.supplier.name}"

class PurchaseOrderItem(models.Model):
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Purchase price at time of order
    total = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

class PurchaseInvoice(models.Model):
    PAYMENT_STATUS = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.PROTECT, related_name='invoices', null=True, blank=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name='invoices')
    invoice_number = models.CharField(max_length=50) # supplier's invoice number
    received_date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='UNPAID')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['supplier', 'invoice_number']

    def __str__(self):
        return f"Inv: {self.invoice_number} ({self.supplier.name})"

class PurchaseReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice = models.ForeignKey(PurchaseInvoice, on_delete=models.PROTECT, related_name='returns')
    return_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    total_refund = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

class PurchaseReturnItem(models.Model):
    purchase_return = models.ForeignKey(PurchaseReturn, on_delete=models.CASCADE, related_name='items')
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    unit_refund = models.DecimalField(max_digits=10, decimal_places=2)


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
    medicine = models.ForeignKey(Medicine, on_delete=models.SET_NULL, null=True, blank=True)
    medicine_name = models.CharField(max_length=255, help_text="Fallback if medicine not in inventory")
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    quantity_prescribed = models.PositiveIntegerField(default=0)


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
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name='sale_items')
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2) # Could be MRP or discounted price
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.medicine.name} x{self.quantity}"

class SaleReturn(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sale = models.ForeignKey(Sale, on_delete=models.PROTECT, related_name='returns')
    return_date = models.DateField(default=timezone.now)
    reason = models.TextField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Return for {self.sale.invoice_number}"
