"""
Appointment CRUD views for the clinic dashboard.
"""
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from apps.appointments.models import Appointment, AppointmentConfig
from apps.clinical.models import Doctor
from apps.patients.models import Patient


class AppointmentListView(View):
    """List appointments with filter support."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        qs = Appointment.objects.select_related("doctor", "patient")

        # Filters
        status = request.GET.get("status")
        if status:
            qs = qs.filter(status=status)

        date_filter = request.GET.get("date")
        if date_filter:
            qs = qs.filter(appointment_date=date_filter)

        doctor_id = request.GET.get("doctor")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)

        context = {
            "appointments": qs[:100],
            "doctors": Doctor.objects.filter(is_active=True),
            "status_choices": Appointment.STATUS_CHOICES,
            "selected_status": status or "",
            "selected_date": date_filter or "",
            "total": qs.count(),
        }
        return render(request, "dashboard/appointments/list.html", context)


class AppointmentCreateView(View):
    """Book a new appointment."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        context = {
            "doctors": Doctor.objects.filter(is_active=True),
            "patients": Patient.objects.all()[:200],
            "type_choices": Appointment.TYPE_CHOICES,
        }
        return render(request, "dashboard/appointments/form.html", context)

    def post(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        patient_id = request.POST.get("patient")
        doctor_id = request.POST.get("doctor")
        apt_date = request.POST.get("appointment_date")
        apt_time = request.POST.get("appointment_time")
        apt_type = request.POST.get("appointment_type", "SCHEDULED")
        notes = request.POST.get("notes", "").strip()
        fee = request.POST.get("fee", 0)

        doctor = get_object_or_404(Doctor, pk=doctor_id)
        patient = None
        patient_name = ""
        if patient_id:
            patient = Patient.objects.filter(pk=patient_id).first()
        if not patient:
            patient_name = request.POST.get("patient_name", "Walk-in")

        Appointment.objects.create(
            patient=patient,
            patient_name=patient_name,
            doctor=doctor,
            appointment_date=apt_date,
            appointment_time=apt_time,
            appointment_type=apt_type,
            notes=notes,
            fee=fee or 0,
        )
        return redirect("/dashboard/appointments/")


class AppointmentDetailView(View):
    """View/manage a single appointment."""

    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        return render(request, "dashboard/appointments/detail.html", {
            "apt": appointment,
            "status_choices": Appointment.STATUS_CHOICES,
        })

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        action = request.POST.get("action")

        if action == "update_status":
            appointment.status = request.POST.get("status", appointment.status)
            if appointment.status == "NO_SHOW":
                appointment.no_show = True
            appointment.save()
        elif action == "cancel":
            appointment.status = "CANCELLED"
            appointment.cancellation_reason = request.POST.get("reason", "")
            appointment.save()
        elif action == "check_in":
            from django.utils.timezone import now
            appointment.check_in_time = now().time()
            appointment.status = "IN_PROGRESS"
            appointment.save()
        elif action == "check_out":
            from django.utils.timezone import now
            appointment.check_out_time = now().time()
            appointment.status = "COMPLETED"
            appointment.save()

        return redirect(f"/dashboard/appointments/{pk}/")
