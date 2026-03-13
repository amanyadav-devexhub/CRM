from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid


# ─────────────────────────────────────────────
# Shared Schema Models (SuperAdmin Managed)
# ─────────────────────────────────────────────

class ItemType(models.Model):
    """
    System-level inventory type defining how items behave.
    e.g., Medicine, Lab Reagent, Equipment.
    Managed by SuperAdmin. Lives in SHARED schema.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    icon = models.CharField(max_length=50, default='inventory_2')
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class ItemCategory(models.Model):
    """
    Fine-grained grouping within an ItemType.
    e.g., Tablets, Capsules under Medicine.
    Managed by SuperAdmin. Lives in SHARED schema.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.ForeignKey(ItemType, on_delete=models.CASCADE, related_name='categories')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['item_type__name', 'name']
        verbose_name_plural = 'Item Categories'

    def __str__(self):
        return f"{self.item_type.name} → {self.name}"


# ─────────────────────────────────────────────
# Tenant Schema Models
# ─────────────────────────────────────────────

class Supplier(models.Model):
    """Generalized supplier record for any inventory type."""
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


class InventoryItem(models.Model):
    """Core inventory item record — universally used across all categories."""
    STATUS_CHOICES = [
        ('IN_STOCK', 'In Stock'),
        ('LOW_STOCK', 'Low Stock'),
        ('OUT_OF_STOCK', 'Out of Stock'),
        ('EXPIRED', 'Expired'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    item_type = models.ForeignKey(
        ItemType, on_delete=models.PROTECT,
        related_name='inventory_items',
        help_text='System-level type (Medicine, Reagent, etc.)'
    )
    item_category = models.ForeignKey(
        ItemCategory, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='inventory_items',
        help_text='Sub-category within the type'
    )
    sku = models.CharField(max_length=100, unique=True, help_text='Stock Keeping Unit')
    barcode = models.CharField(max_length=100, blank=True, null=True)
    unit = models.CharField(max_length=50, default='pcs', help_text='e.g., pcs, boxes, ml, kits')
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='inventory_images/', null=True, blank=True)

    # Stock thresholds
    min_stock_level = models.PositiveIntegerField(default=10, help_text='Low stock alert trigger')

    # Computed fields
    total_stock = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='IN_STOCK')

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True, related_name='items')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.sku})"

    def update_stock_status(self):
        """Recalculate total_stock from batches and update status."""
        from django.db.models import Sum
        total = self.batches.filter(is_active=True).aggregate(
            total=Sum('quantity')
        )['total'] or 0
        self.total_stock = total

        # Check expiry across all batches
        has_expired = self.batches.filter(
            is_active=True,
            expiry_date__lt=timezone.now().date()
        ).exists()

        if has_expired and total == 0:
            self.status = 'EXPIRED'
        elif total == 0:
            self.status = 'OUT_OF_STOCK'
        elif total <= self.min_stock_level:
            self.status = 'LOW_STOCK'
        else:
            self.status = 'IN_STOCK'
        self.save(update_fields=['total_stock', 'status', 'updated_at'])


class InventoryBatch(models.Model):
    """Per-batch tracking for FIFO/FEFO inventory management."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='batches')
    batch_number = models.CharField(max_length=100)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Pricing
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    mrp = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='GST %')

    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['expiry_date', 'created_at']

    def __str__(self):
        return f"{self.item.name} — Batch {self.batch_number}"

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def is_expiring_soon(self):
        if self.expiry_date:
            return (self.expiry_date - timezone.now().date()).days <= 30 and not self.is_expired
        return False


class StockTransaction(models.Model):
    """Immutable audit log for all inventory movements."""
    TRANSACTION_TYPES = [
        ('IN', 'Stock In'),
        ('OUT', 'Stock Out'),
        ('ADJUST', 'Adjustment'),
        ('RETURN', 'Return'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name='transactions')
    batch = models.ForeignKey(InventoryBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    transaction_type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    quantity = models.DecimalField(max_digits=12, decimal_places=2)
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, related_name='global_inventory_transactions'
    )
    notes = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.get_transaction_type_display()} — {self.item.name} ({self.quantity})"


class PurchaseOrder(models.Model):
    """Purchase order for inventory procurement."""
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

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"PO {self.order_number} — {self.supplier.name}"


class PurchaseOrderItem(models.Model):
    """Line item on a purchase order."""
    purchase_order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name='po_items')
    quantity = models.PositiveIntegerField()
    received_quantity = models.PositiveIntegerField(default=0)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        self.total = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} x{self.quantity}"
