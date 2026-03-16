# apps/patients/template_views.py — template syntax fixes applied
"""
Template-based views for Patient management.
These render full HTML pages (not API JSON responses).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q
from apps.utils.mixins import HasTenantPermissionMixin

from .models import (
    Patient, MedicalHistory, Allergy,
    Insurance, PatientDocument, EmergencyContact,
)

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


class PatientListView(HasTenantPermissionMixin, View):
    """List all patients with search and filters."""
    required_permission = ["patients.view_records", "patients.register"]

    def get(self, request):
        try:
            if request.user.doctor_profile:
                patients = Patient.objects.filter(assigned_doctor=request.user.doctor_profile)
            else:
                patients = Patient.objects.all()
        except getattr(request.user, 'DoesNotExist', Exception):
            patients = Patient.objects.all()
        except Exception:
            patients = Patient.objects.all()

        search = request.GET.get("search", "").strip()
        gender = request.GET.get("gender", "").strip()
        blood = request.GET.get("blood_group", "").strip()

        if search:
            patients = patients.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(patient_id__icontains=search)
                | Q(email__icontains=search)
            )
        if gender:
            patients = patients.filter(gender=gender)
        if blood:
            patients = patients.filter(blood_group=blood)

        return render(request, "patients/patient_list.html", {
            "patients": patients,
            "search_query": search,
            "gender_filter": gender,
            "blood_filter": blood,
            "blood_groups": BLOOD_GROUPS,
        })


class PatientDetailView(View):
    """Full patient profile with all related records."""

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        from apps.inventory.models import InventoryItem, StockTransaction
        
        # Consumables for bedside tracking
        consumables = InventoryItem.objects.filter(
            item_type__code__in=['CONSUMABLE', 'MEDICAL_SUPPLY', 'SURGICAL_ITEM']
        ).select_related('item_type')
        
        # Recent consumption for this patient
        recent_consumption = StockTransaction.objects.filter(
            patient_id=patient.id,
            transaction_type='OUT'
        ).select_related('item', 'performed_by').order_by('-timestamp')[:10]

        return render(request, "patients/patient_detail.html", {
            "patient": patient,
            "medical_history": patient.medical_history.all(),
            "allergies": patient.allergies.all(),
            "insurance": patient.insurance_policies.all(),
            "documents": patient.documents.all(),
            "emergency_contacts": patient.emergency_contacts.all(),
            "lab_orders": patient.lab_orders.all().order_by('-ordered_at'),
            "inventory_items": consumables,
            "recent_consumption": recent_consumption,
        })


class PatientCreateView(View):
    """Create a new patient."""

    def get(self, request):
        from apps.clinical.models import Doctor
        doctors = Doctor.objects.filter(is_active=True)
        return render(request, "patients/patient_form.html", {
            "patient": None,
            "blood_groups": BLOOD_GROUPS,
            "doctors": doctors,
        })

    def post(self, request):
        data = request.POST
        try:
            patient = Patient.objects.create(
                first_name=data["first_name"],
                last_name=data["last_name"],
                date_of_birth=data.get("date_of_birth") or None,
                gender=data["gender"],
                blood_group=data.get("blood_group") or "",
                marital_status=data.get("marital_status") or "",
                phone=data["phone"],
                email=data.get("email") or "",
                preferred_language=data.get("preferred_language") or "English",
                notes=data.get("notes") or "",
                assigned_doctor_id=data.get("assigned_doctor") or None,
            )
            return redirect(f"/patients/{patient.id}/")
        except Exception as e:
            from apps.clinical.models import Doctor
            doctors = Doctor.objects.filter(is_active=True)
            return render(request, "patients/patient_form.html", {
                "patient": None,
                "blood_groups": BLOOD_GROUPS,
                "doctors": doctors,
                "form_errors": str(e),
            })


class PatientEditView(View):
    """Edit an existing patient."""

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        from apps.clinical.models import Doctor
        doctors = Doctor.objects.filter(is_active=True)
        return render(request, "patients/patient_form.html", {
            "patient": patient,
            "blood_groups": BLOOD_GROUPS,
            "doctors": doctors,
        })

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        data = request.POST
        try:
            patient.first_name = data["first_name"]
            patient.last_name = data["last_name"]
            patient.date_of_birth = data.get("date_of_birth") or None
            patient.gender = data["gender"]
            patient.blood_group = data.get("blood_group") or ""
            patient.marital_status = data.get("marital_status") or ""
            patient.phone = data["phone"]
            patient.email = data.get("email") or ""
            patient.preferred_language = data.get("preferred_language") or "English"
            patient.notes = data.get("notes") or ""
            patient.assigned_doctor_id = data.get("assigned_doctor") or None
            patient.save()
            return redirect(f"/patients/{patient.id}/")
        except Exception as e:
            from apps.clinical.models import Doctor
            doctors = Doctor.objects.filter(is_active=True)
            return render(request, "patients/patient_form.html", {
                "patient": patient,
                "blood_groups": BLOOD_GROUPS,
                "doctors": doctors,
                "form_errors": str(e),
            })


class PatientDeleteView(View):
    """Soft-delete a patient and redirect to the list."""

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        patient.delete()  # soft delete via SoftDeleteMixin
        return redirect("/patients/")


# ──────────────────────────────────────────────
# Medical History inline CRUD (modal based)
# ──────────────────────────────────────────────

class MedicalHistoryAddView(View):
    """Add a new medical history record."""

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        data = request.POST
        
        MedicalHistory.objects.create(
            patient=patient,
            condition=data.get("condition", "").strip(),
            diagnosis_date=data.get("diagnosis_date") or None,
            status=data.get("status", MedicalHistory.Status.ACTIVE),
            notes=data.get("notes", "").strip()
        )
        
        return redirect(f"/patients/{patient.id}/")


class MedicalHistoryEditView(View):
    """Edit an existing medical history record."""

    def post(self, request, pk, mh_id):
        patient = get_object_or_404(Patient, pk=pk)
        record = get_object_or_404(MedicalHistory, pk=mh_id, patient=patient)
        data = request.POST
        
        record.condition = data.get("condition", record.condition).strip()
        record.diagnosis_date = data.get("diagnosis_date") or None
        record.status = data.get("status", record.status)
        record.notes = data.get("notes", record.notes).strip()
        record.save()
        
        return redirect(f"/patients/{patient.id}/")


class MedicalHistoryDeleteView(View):
    """Delete a medical history record."""

    def post(self, request, pk, mh_id):
        patient = get_object_or_404(Patient, pk=pk)
        record = get_object_or_404(MedicalHistory, pk=mh_id, patient=patient)
        record.delete()
        
        return redirect(f"/patients/{patient.id}/")


# ──────────────────────────────────────────────
# Patient Documents inline CRUD (modal based)
# ──────────────────────────────────────────────

class PatientDocumentUploadView(View):
    """Upload a new patient document."""

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        data = request.POST
        files = request.FILES
        
        if "file" in files:
            PatientDocument.objects.create(
                patient=patient,
                file=files["file"],
                document_type=data.get("document_type", PatientDocument.DocumentType.OTHER),
                title=data.get("title", "Untitled Document").strip(),
                description=data.get("description", "").strip(),
                uploaded_by=request.user if request.user.is_authenticated else None
            )
            
        return redirect(f"/patients/{patient.id}/")


class PatientDocumentDeleteView(View):
    """Delete a patient document."""

    def post(self, request, pk, doc_id):
        patient = get_object_or_404(Patient, pk=pk)
        document = get_object_or_404(PatientDocument, pk=doc_id, patient=patient)
        
        # The physical file will be kept or deleted depending on your storage backend semantics
        # If using standard FileField, deleting the model instance doesn't automatically delete the file
        # To delete the file physically: document.file.delete(save=False)
        document.file.delete(save=False)
        document.delete()
        
        return redirect(f"/patients/{patient.id}/")
