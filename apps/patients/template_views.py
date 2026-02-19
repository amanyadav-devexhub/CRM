# apps/patients/template_views.py — template syntax fixes applied
"""
Template-based views for Patient management.
These render full HTML pages (not API JSON responses).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.db.models import Q

from .models import (
    Patient, MedicalHistory, Allergy,
    Insurance, PatientDocument, EmergencyContact,
)

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]


class PatientListView(View):
    """List all patients with search and filters."""

    def get(self, request):
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
        return render(request, "patients/patient_detail.html", {
            "patient": patient,
            "medical_history": patient.medical_history.all(),
            "allergies": patient.allergies.all(),
            "insurance": patient.insurance_policies.all(),
            "documents": patient.documents.all(),
            "emergency_contacts": patient.emergency_contacts.all(),
        })


class PatientCreateView(View):
    """Create a new patient."""

    def get(self, request):
        return render(request, "patients/patient_form.html", {
            "patient": None,
            "blood_groups": BLOOD_GROUPS,
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
            )
            return redirect(f"/patients/{patient.id}/")
        except Exception as e:
            return render(request, "patients/patient_form.html", {
                "patient": None,
                "blood_groups": BLOOD_GROUPS,
                "form_errors": str(e),
            })


class PatientEditView(View):
    """Edit an existing patient."""

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        return render(request, "patients/patient_form.html", {
            "patient": patient,
            "blood_groups": BLOOD_GROUPS,
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
            patient.save()
            return redirect(f"/patients/{patient.id}/")
        except Exception as e:
            return render(request, "patients/patient_form.html", {
                "patient": patient,
                "blood_groups": BLOOD_GROUPS,
                "form_errors": str(e),
            })


class PatientDeleteView(View):
    """Soft-delete a patient and redirect to the list."""

    def post(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk)
        patient.delete()  # soft delete via SoftDeleteMixin
        return redirect("/patients/")
