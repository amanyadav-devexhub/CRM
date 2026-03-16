from django.contrib import admin
from .models import (
    Sale, SaleItem, SaleReturn,
    Prescription, PrescriptionItem
)

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
