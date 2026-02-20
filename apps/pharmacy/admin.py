from django.contrib import admin
from .models import Medicine, Sale, SaleItem, Prescription


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'stock', 'price', 'expiry_date', 'status')
    list_filter = ('status', 'category')
    search_fields = ('name', 'sku', 'batch_number')


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'subtotal', 'tax', 'grand_total', 'created_at')
    inlines = [SaleItemInline]


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'doctor_name', 'status', 'created_at')
    list_filter = ('status',)
    search_fields = ('patient_name', 'doctor_name')
