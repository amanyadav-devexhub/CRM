from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'doctor', 'appointment_date', 'appointment_time', 'status', 'fee')
    list_filter = ('status', 'appointment_date')
    search_fields = ('patient_name', 'doctor__name')
