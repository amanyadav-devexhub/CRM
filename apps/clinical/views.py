"""
Clinical views for patient records (Notes, Prescriptions).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.utils.mixins import HasTenantPermissionMixin
from apps.clinical.models import ClinicalNote, Prescription, PrescriptionItem
from apps.patients.models import Patient
from apps.clinical.models import Doctor


class ClinicalNoteListView(HasTenantPermissionMixin, View):
    """List clinical notes for a patient or overall."""
    required_permission = "patients.view_records"
    def get(self, request):
        patient_id = request.GET.get("patient")
        notes = ClinicalNote.objects.select_related("patient", "doctor")
        if patient_id:
            notes = notes.filter(patient_id=patient_id)
        
        context = {
            "notes": notes[:100],
            "total": notes.count(),
            "patient_id": patient_id,
        }
        return render(request, "dashboard/clinical/note_list.html", context)


class ClinicalNoteCreateView(HasTenantPermissionMixin, View):
    """Create a new SOAP note."""
    required_permission = "patients.edit_records"
    def get(self, request):
        patient_id = request.GET.get("patient")
        context = {
            "patients": Patient.objects.all()[:200],
            "doctors": Doctor.objects.filter(is_active=True),
            "selected_patient": patient_id,
        }
        return render(request, "dashboard/clinical/note_form.html", context)

    def post(self, request):
        patient = get_object_or_404(Patient, pk=request.POST.get("patient"))
        doctor = get_object_or_404(Doctor, pk=request.POST.get("doctor"))
        
        ClinicalNote.objects.create(
            patient=patient,
            doctor=doctor,
            subjective=request.POST.get("subjective", ""),
            objective=request.POST.get("objective", ""),
            assessment=request.POST.get("assessment", ""),
            plan=request.POST.get("plan", ""),
        )
        return redirect(f"/patients/{patient.pk}/")


class ClinicalNoteEditView(HasTenantPermissionMixin, View):
    """Edit an existing SOAP note."""
    required_permission = "patients.edit_records"

    def get(self, request, pk):
        note = get_object_or_404(ClinicalNote, pk=pk)
        context = {
            "note": note,
            "patients": Patient.objects.all()[:200],
            "doctors": Doctor.objects.filter(is_active=True),
            "editing": True,
        }
        return render(request, "dashboard/clinical/note_form.html", context)

    def post(self, request, pk):
        note = get_object_or_404(ClinicalNote, pk=pk)
        
        patient = get_object_or_404(Patient, pk=request.POST.get("patient"))
        doctor = get_object_or_404(Doctor, pk=request.POST.get("doctor"))
        
        note.patient = patient
        note.doctor = doctor
        note.subjective = request.POST.get("subjective", "")
        note.objective = request.POST.get("objective", "")
        note.assessment = request.POST.get("assessment", "")
        note.plan = request.POST.get("plan", "")
        note.save()
        
        return redirect(f"/patients/{patient.pk}/")


class PrescriptionCreateView(HasTenantPermissionMixin, View):
    """Create a prescription with items."""
    required_permission = "prescriptions.issue"
    def get(self, request):
        patient_id = request.GET.get("patient")
        context = {
            "patients": Patient.objects.all()[:200],
            "doctors": Doctor.objects.filter(is_active=True),
            "selected_patient": patient_id,
        }
        return render(request, "dashboard/clinical/prescription_form.html", context)

    def post(self, request):
        patient = get_object_or_404(Patient, pk=request.POST.get("patient"))
        doctor = get_object_or_404(Doctor, pk=request.POST.get("doctor"))
        
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=doctor,
            notes=request.POST.get("notes", ""),
        )

        meds = request.POST.getlist("medicine_name")
        dosages = request.POST.getlist("dosage")
        freqs = request.POST.getlist("frequency")
        durations = request.POST.getlist("duration")
        instructions = request.POST.getlist("instructions")

        for m, d, f, dur, nst in zip(meds, dosages, freqs, durations, instructions):
            if m.strip():
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    medicine_name=m,
                    dosage=d,
                    frequency=f,
                    duration=dur,
                    instructions=nst
                )

        return redirect(f"/patients/{patient.pk}/")


class PrescriptionDetailView(HasTenantPermissionMixin, View):
    """View a single prescription with all its items."""
    required_permission = ["patients.view_records", "patients.register", "prescriptions.edit", "prescriptions.issue"]

    def get(self, request, pk):
        prescription = get_object_or_404(
            Prescription.objects.select_related("patient", "doctor").prefetch_related("items"),
            pk=pk
        )
        context = {
            "rx": prescription,
            "items": prescription.items.all(),
            "patient": prescription.patient,
            "doctor": prescription.doctor,
        }
        return render(request, "dashboard/clinical/prescription_detail.html", context)


class PrescriptionListView(HasTenantPermissionMixin, View):
    """List all prescriptions."""
    required_permission = "prescriptions.edit"
    def get(self, request):
        patient_id = request.GET.get("patient")
        prescriptions = Prescription.objects.select_related("patient", "doctor").prefetch_related("items")
        if patient_id:
            prescriptions = prescriptions.filter(patient_id=patient_id)
        
        context = {
            "prescriptions": prescriptions[:100],
            "total": prescriptions.count(),
            "patient_id": patient_id,
        }
        return render(request, "dashboard/clinical/prescription_list.html", context)
