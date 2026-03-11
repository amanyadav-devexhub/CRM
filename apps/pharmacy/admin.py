from django.contrib import admin
from .models import (
    Supplier, Medicine, PurchaseOrder, PurchaseOrderItem, PurchaseInvoice,
    PurchaseReturn, PurchaseReturnItem, Sale, SaleItem, SaleReturn,
    Prescription, PrescriptionItem
)

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('name', 'contact_person', 'phone', 'is_active')
    search_fields = ('name', 'email', 'phone')
    list_filter = ('is_active',)

@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'stock', 'price', 'status')
    list_filter = ('category', 'status')
    search_fields = ('name', 'sku', 'barcode')

class PurchaseOrderItemInline(admin.TabularInline):
    model = PurchaseOrderItem
    extra = 1

@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(admin.ModelAdmin):
    list_display = ('order_number', 'supplier', 'order_date', 'status', 'total_amount')
    list_filter = ('status', 'supplier')
    search_fields = ('order_number',)
    inlines = [PurchaseOrderItemInline]

@admin.register(PurchaseInvoice)
class PurchaseInvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'supplier', 'received_date', 'total_amount', 'payment_status')
    list_filter = ('payment_status', 'supplier')
    search_fields = ('invoice_number',)

class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 1

@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'payment_mode', 'grand_total', 'created_at')
    list_filter = ('payment_mode',)
    search_fields = ('invoice_number',)
    inlines = [SaleItemInline]

@admin.register(SaleReturn)
class SaleReturnAdmin(admin.ModelAdmin):
    list_display = ('sale', 'return_date', 'refund_amount')

class PrescriptionItemInline(admin.TabularInline):
    model = PrescriptionItem
    extra = 1

@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'doctor_name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('patient_name', 'doctor_name')
    inlines = [PrescriptionItemInline]
