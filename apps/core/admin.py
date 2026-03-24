from django.contrib import admin
from .models import Country, Currency, Language, Timezone, DateFormat

@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ['name', 'iso_code', 'dial_code', 'status']
    list_filter = ['status']
    search_fields = ['name', 'iso_code', 'dial_code']
    fieldsets = (
        (None, {
            'fields': ('name', 'iso_code', 'dial_code', 'flag_logo', 'status')
        }),
        ('Regional Defaults', {
            'fields': ('primary_currency', 'primary_language', 'primary_timezone')
        }),
    )

@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'symbol', 'status']
    list_filter = ['status']
    search_fields = ['name', 'code']

@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'native_name', 'status']
    list_filter = ['status']
    search_fields = ['name', 'code']

@admin.register(Timezone)
class TimezoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'offset_label', 'status']
    list_filter = ['status']
    search_fields = ['name']

@admin.register(DateFormat)
class DateFormatAdmin(admin.ModelAdmin):
    list_display = ['label', 'format_code', 'status']
    list_filter = ['status']
    search_fields = ['label', 'format_code']
