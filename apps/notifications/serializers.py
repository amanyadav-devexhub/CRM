from rest_framework import serializers
from apps.notifications.models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    Returns notification data for API responses.
    """
    
    # Optional: Add readable type display
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'body',
            'is_read',
            'is_archived',
            'priority',
            'action_url',
            'action_text',
            'image_url',
            'metadata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
            'type_display',
        ]


class NotificationListSerializer(serializers.ModelSerializer):
    """
    Lightweight serializer for list views (excludes metadata).
    """
    
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Notification
        fields = [
            'id',
            'type',
            'type_display',
            'title',
            'body',
            'is_read',
            'priority',
            'action_url',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'type_display']


class NotificationMarkReadSerializer(serializers.Serializer):
    """
    Serializer for marking notifications as read.
    """
    is_read = serializers.BooleanField(default=True)