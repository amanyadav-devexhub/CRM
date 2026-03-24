from django.contrib import admin
from .models import Client, Domain, Category, Tenant

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'icon', 'color', 'is_active', 'sort_order']
    list_filter = ['is_active', 'color']
    search_fields = ['name', 'code']

@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'subdomain', 'category', 'country', 'is_active']
    list_filter = ['is_active', 'category', 'country']
    search_fields = ['name', 'subdomain', 'phone']
    fieldsets = (
        (None, {
            'fields': ('name', 'subdomain', 'category', 'is_active', 'logo')
        }),
        ('Location & Localization', {
            'fields': ('address', 'country', 'phone', 'timezone', 'currency', 'language', 'date_format')
        }),
        ('Tax & Registration', {
            'fields': ('gst_number', 'registration_number')
        }),
        ('Dynamic Settings', {
            'fields': ('working_hours', 'holidays', 'emergency_available')
        }),
    )

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['name', 'paid_until', 'on_trial', 'created_on']
    list_filter = ['on_trial']
    search_fields = ['name']

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ['domain', 'tenant', 'is_primary']
    list_filter = ['is_primary']
    search_fields = ['domain']
