from rest_framework import serializers
from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(
        source="get_type_display", read_only=True
    )

    class Meta:
        model = Notification
        fields = [
            "id", "user", "type", "type_display",
            "title", "body", "is_read",
            "action_url", "created_at",
        ]
        read_only_fields = ["user"]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = [
            "id", "user",
            "email_enabled", "sms_enabled",
            "push_enabled", "in_app_enabled",
            "quiet_hours_start", "quiet_hours_end",
            "created_at", "updated_at",
        ]
        read_only_fields = ["user"]
