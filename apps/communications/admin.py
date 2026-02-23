from django.contrib import admin
from .models import MessageTemplate, Message, Campaign, Feedback


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ["name", "channel", "is_active", "created_at"]
    list_filter = ["channel", "is_active"]
    search_fields = ["name", "body"]


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ["patient", "channel", "status", "sent_at", "created_at"]
    list_filter = ["channel", "status"]
    search_fields = ["patient__first_name", "patient__last_name", "subject"]
    raw_id_fields = ["patient", "template", "sent_by"]


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ["name", "status", "total_recipients", "sent_count", "failed_count", "scheduled_at"]
    list_filter = ["status"]
    search_fields = ["name"]
    raw_id_fields = ["template", "created_by"]


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ["patient", "rating", "appointment", "submitted_at"]
    list_filter = ["rating"]
    search_fields = ["patient__first_name", "patient__last_name", "comments"]
    raw_id_fields = ["patient", "appointment"]
