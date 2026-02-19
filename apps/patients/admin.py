from django.contrib import admin
from .models import (
    Patient, PatientTag, Address, EmergencyContact,
    MedicalHistory, Allergy, Insurance, PatientDocument, FamilyLink,
)


# ──────────────────────────────────────────────
# Inlines (shown inside the Patient admin page)
# ──────────────────────────────────────────────
class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


class EmergencyContactInline(admin.TabularInline):
    model = EmergencyContact
    extra = 0


class MedicalHistoryInline(admin.TabularInline):
    model = MedicalHistory
    extra = 0


class AllergyInline(admin.TabularInline):
    model = Allergy
    extra = 0


class InsuranceInline(admin.TabularInline):
    model = Insurance
    extra = 0


class PatientDocumentInline(admin.TabularInline):
    model = PatientDocument
    extra = 0
    readonly_fields = ["uploaded_by"]


class FamilyLinkInline(admin.TabularInline):
    model = FamilyLink
    fk_name = "patient"
    extra = 0


# ──────────────────────────────────────────────
# Model Admin registrations
# ──────────────────────────────────────────────
@admin.register(PatientTag)
class PatientTagAdmin(admin.ModelAdmin):
    list_display = ["name", "color", "created_at"]
    search_fields = ["name"]


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = [
        "patient_id", "first_name", "last_name",
        "phone", "gender", "blood_group", "created_at",
    ]
    list_filter = ["gender", "blood_group", "is_deleted", "tags"]
    search_fields = ["first_name", "last_name", "phone", "email", "patient_id"]
    readonly_fields = ["patient_id", "created_at", "updated_at"]
    filter_horizontal = ["tags"]
    inlines = [
        AddressInline,
        EmergencyContactInline,
        MedicalHistoryInline,
        AllergyInline,
        InsuranceInline,
        PatientDocumentInline,
        FamilyLinkInline,
    ]


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ["patient", "city", "state", "is_primary"]
    list_filter = ["is_primary", "country"]
    search_fields = ["patient__first_name", "patient__last_name", "city"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["patient", "name", "phone", "relationship"]
    search_fields = ["name", "patient__first_name", "patient__last_name"]


@admin.register(MedicalHistory)
class MedicalHistoryAdmin(admin.ModelAdmin):
    list_display = ["patient", "condition", "status", "diagnosis_date"]
    list_filter = ["status"]
    search_fields = ["condition", "patient__first_name", "patient__last_name"]


@admin.register(Allergy)
class AllergyAdmin(admin.ModelAdmin):
    list_display = ["patient", "allergen", "severity"]
    list_filter = ["severity"]
    search_fields = ["allergen", "patient__first_name", "patient__last_name"]


@admin.register(Insurance)
class InsuranceAdmin(admin.ModelAdmin):
    list_display = ["patient", "provider", "policy_number", "valid_from", "valid_to", "is_active"]
    list_filter = ["is_active", "provider"]
    search_fields = ["policy_number", "provider", "patient__first_name", "patient__last_name"]


@admin.register(PatientDocument)
class PatientDocumentAdmin(admin.ModelAdmin):
    list_display = ["patient", "title", "document_type", "created_at"]
    list_filter = ["document_type"]
    search_fields = ["title", "patient__first_name", "patient__last_name"]


@admin.register(FamilyLink)
class FamilyLinkAdmin(admin.ModelAdmin):
    list_display = ["patient", "related_patient", "relationship"]
    list_filter = ["relationship"]
