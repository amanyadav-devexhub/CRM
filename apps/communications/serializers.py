from rest_framework import serializers
from .models import MessageTemplate, Message, Campaign, Feedback


# ──────────────────────────────────────────────
# MessageTemplate
# ──────────────────────────────────────────────
class MessageTemplateSerializer(serializers.ModelSerializer):
    channel_display = serializers.CharField(
        source="get_channel_display", read_only=True
    )

    class Meta:
        model = MessageTemplate
        fields = [
            "id", "name", "channel", "channel_display",
            "subject", "body", "variables", "is_active",
            "created_at", "updated_at",
        ]


# ──────────────────────────────────────────────
# Message
# ──────────────────────────────────────────────
class MessageListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for message list views."""
    patient_name = serializers.SerializerMethodField()
    channel_display = serializers.CharField(
        source="get_channel_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )

    class Meta:
        model = Message
        fields = [
            "id", "patient", "patient_name",
            "channel", "channel_display",
            "subject", "status", "status_display",
            "sent_at", "created_at",
        ]

    def get_patient_name(self, obj):
        return obj.patient.full_name


class MessageDetailSerializer(serializers.ModelSerializer):
    """Full serializer for message detail/create."""
    patient_name = serializers.SerializerMethodField()
    channel_display = serializers.CharField(
        source="get_channel_display", read_only=True
    )
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = Message
        fields = [
            "id", "patient", "patient_name",
            "template", "template_name",
            "channel", "channel_display",
            "subject", "body",
            "status", "status_display",
            "sent_at", "error_message", "sent_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["sent_by", "sent_at"]

    def get_patient_name(self, obj):
        return obj.patient.full_name

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None


# ──────────────────────────────────────────────
# Campaign
# ──────────────────────────────────────────────
class CampaignListSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    delivery_rate = serializers.FloatField(read_only=True)
    template_name = serializers.SerializerMethodField()

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "template", "template_name",
            "status", "status_display",
            "scheduled_at", "total_recipients",
            "sent_count", "failed_count", "delivery_rate",
            "created_at",
        ]

    def get_template_name(self, obj):
        return obj.template.name if obj.template else None


class CampaignDetailSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(
        source="get_status_display", read_only=True
    )
    delivery_rate = serializers.FloatField(read_only=True)

    class Meta:
        model = Campaign
        fields = [
            "id", "name", "template",
            "segment_filter", "scheduled_at",
            "status", "status_display",
            "total_recipients", "sent_count", "failed_count",
            "delivery_rate", "created_by",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "created_by", "total_recipients",
            "sent_count", "failed_count",
        ]


# ──────────────────────────────────────────────
# Feedback
# ──────────────────────────────────────────────
class FeedbackSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()

    class Meta:
        model = Feedback
        fields = [
            "id", "patient", "patient_name",
            "appointment", "rating", "comments",
            "submitted_at", "created_at",
        ]

    def get_patient_name(self, obj):
        return obj.patient.full_name

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value
