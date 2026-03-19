from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    sender_name  = serializers.SerializerMethodField()
    time_ago     = serializers.SerializerMethodField()
    type_display = serializers.SerializerMethodField()
    type_icon    = serializers.SerializerMethodField()

    class Meta:
        model  = Notification
        fields = [
            "id", "title", "message",
            "notification_type", "type_display", "type_icon",
            "priority", "action_url", "action_id", "extra_data",
            "is_read", "read_at", "created_at",
            "sender_name", "time_ago",
        ]
        read_only_fields = fields

    def get_sender_name(self, obj) -> str:
        if obj.sender:
            return obj.sender.get_full_name() or obj.sender.username
        return "System"

    def get_time_ago(self, obj) -> str:
        from django.utils import timezone
        from django.utils.timesince import timesince
        return timesince(obj.created_at, timezone.now())

    def get_type_display(self, obj) -> str:
        return obj.get_notification_type_display()

    def get_type_icon(self, obj) -> str:
        return {
            "appointment":  "calendar",
            "billing":      "credit-card",
            "lab_result":   "flask",
            "prescription": "pill",
            "emergency":    "alert-triangle",
            "general":      "bell",
        }.get(obj.notification_type, "bell")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model  = NotificationPreference
        fields = [
            "appointment_enabled", "billing_enabled", "lab_result_enabled",
            "prescription_enabled", "emergency_enabled", "general_enabled",
            "in_app_enabled", "email_enabled", "sms_enabled",
        ]


class NotificationCountSerializer(serializers.Serializer):
    unread_count = serializers.IntegerField()
    total_count  = serializers.IntegerField()