"""
Clinical views for patient records (Notes, Prescriptions).
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.clinical.models import ClinicalNote, Prescription, PrescriptionItem
from apps.patients.models import Patient
from apps.clinical.models import Doctor


class ClinicalNoteListView(View):
    """List clinical notes for a patient or overall."""
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


class ClinicalNoteCreateView(View):
    """Create a new SOAP note."""
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


class PrescriptionCreateView(View):
    """Create a prescription with items."""
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


class PrescriptionListView(View):
    """List all prescriptions."""
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
