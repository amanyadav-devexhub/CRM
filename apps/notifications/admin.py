from django.contrib import admin
from .models import Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["title", "user", "type", "is_read", "created_at"]
    list_filter = ["type", "is_read"]
    search_fields = ["title", "body", "user__username"]
    raw_id_fields = ["user"]


@admin.register(NotificationPreference)
class NotificationPreferenceAdmin(admin.ModelAdmin):
    list_display = [
        "user", "email_enabled", "sms_enabled",
        "push_enabled", "in_app_enabled",
    ]
    raw_id_fields = ["user"]
