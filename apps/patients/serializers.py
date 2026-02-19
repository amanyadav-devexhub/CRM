from rest_framework import serializers
from .models import (
    Patient, PatientTag, Address, EmergencyContact,
    MedicalHistory, Allergy, Insurance, PatientDocument, FamilyLink,
)


# ──────────────────────────────────────────────
# Sub-resource serializers
# ──────────────────────────────────────────────

class PatientTagSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatientTag
        fields = ["id", "name", "color", "description"]


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            "id", "street", "city", "state",
            "zip_code", "country", "is_primary",
            "created_at", "updated_at",
        ]


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmergencyContact
        fields = [
            "id", "name", "phone", "relationship",
            "created_at", "updated_at",
        ]


class MedicalHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistory
        fields = [
            "id", "condition", "diagnosis_date",
            "notes", "status",
            "created_at", "updated_at",
        ]


class AllergySerializer(serializers.ModelSerializer):
    class Meta:
        model = Allergy
        fields = [
            "id", "allergen", "severity", "reaction",
            "created_at", "updated_at",
        ]


class InsuranceSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Insurance
        fields = [
            "id", "provider", "policy_number", "group_number",
            "valid_from", "valid_to", "is_active", "is_expired",
            "created_at", "updated_at",
        ]


class PatientDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = PatientDocument
        fields = [
            "id", "file", "document_type", "title",
            "description", "uploaded_by", "uploaded_by_name",
            "created_at", "updated_at",
        ]
        read_only_fields = ["uploaded_by"]

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return obj.uploaded_by.get_full_name() or obj.uploaded_by.username
        return None


class FamilyLinkSerializer(serializers.ModelSerializer):
    related_patient_name = serializers.SerializerMethodField()

    class Meta:
        model = FamilyLink
        fields = [
            "id", "related_patient", "related_patient_name",
            "relationship", "created_at",
        ]

    def get_related_patient_name(self, obj):
        return obj.related_patient.full_name


# ──────────────────────────────────────────────
# Patient serializers
# ──────────────────────────────────────────────

class PatientListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""
    tags = PatientTagSerializer(many=True, read_only=True)
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_id", "full_name",
            "first_name", "last_name",
            "phone", "email", "gender",
            "age", "tags", "created_at",
        ]


class PatientDetailSerializer(serializers.ModelSerializer):
    """Full serializer with nested sub-resources for detail view."""
    tags = PatientTagSerializer(many=True, read_only=True)
    addresses = AddressSerializer(many=True, read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    medical_history = MedicalHistorySerializer(many=True, read_only=True)
    allergies = AllergySerializer(many=True, read_only=True)
    insurance_policies = InsuranceSerializer(many=True, read_only=True)
    documents = PatientDocumentSerializer(many=True, read_only=True)
    family_links = FamilyLinkSerializer(many=True, read_only=True)
    age = serializers.IntegerField(read_only=True)
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Patient
        fields = [
            "id", "patient_id", "full_name",
            "first_name", "last_name", "date_of_birth", "age",
            "gender", "blood_group",
            "email", "phone", "secondary_phone",
            "profile_picture", "notes",
            "tags", "addresses", "emergency_contacts",
            "medical_history", "allergies",
            "insurance_policies", "documents", "family_links",
            "created_at", "updated_at",
        ]


class PatientCreateUpdateSerializer(serializers.ModelSerializer):
    """Write serializer for creating / updating patients."""
    tag_ids = serializers.PrimaryKeyRelatedField(
        queryset=PatientTag.objects.all(),
        many=True, required=False, source="tags",
    )

    class Meta:
        model = Patient
        fields = [
            "first_name", "last_name", "date_of_birth",
            "gender", "blood_group",
            "email", "phone", "secondary_phone",
            "profile_picture", "notes", "tag_ids",
        ]

    def create(self, validated_data):
        tags = validated_data.pop("tags", [])
        patient = Patient.objects.create(**validated_data)
        if tags:
            patient.tags.set(tags)
        return patient

    def update(self, instance, validated_data):
        tags = validated_data.pop("tags", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if tags is not None:
            instance.tags.set(tags)
        return instance
