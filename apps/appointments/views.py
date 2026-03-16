"""
Appointment CRUD views for the clinic dashboard.
"""
import json
from datetime import datetime, timedelta

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.http import JsonResponse
from django.utils.timezone import now
from django.db import transaction
from apps.appointments.models import Appointment, AppointmentConfig, AppointmentActivity
from apps.clinical.models import Doctor, DoctorSlot
from apps.patients.models import Patient


def log_activity(appointment, action, user=None, notes='', old_status='', new_status=''):
    """Helper to create an activity log entry."""
    AppointmentActivity.objects.create(
        appointment=appointment,
        action=action,
        performed_by=user,
        old_status=old_status,
        new_status=new_status,
        notes=notes,
    )


def get_available_slots(doctor, date):
    """
    Compute available time slots for a doctor on a given date.
    Returns list of dicts: [{"time": "09:00", "display": "09:00 AM", "available": True/False}, ...]
    Skips past time slots when the date is today.
    """
    doctor_slots = DoctorSlot.objects.filter(
        doctor=doctor, schedule_date=date, is_active=True
    ).order_by("start_time")

    if not doctor_slots.exists():
        return []

    # Get existing bookings for this doctor on this date (non-cancelled)
    booked = Appointment.objects.filter(
        doctor=doctor,
        appointment_date=date,
    ).exclude(
        status__in=["CANCELLED"]
    ).values_list("appointment_time", flat=True)

    booked_times = set(str(t.strftime("%H:%M")) for t in booked)

    # If booking for today, skip slots that are already in the past
    is_today = (date == datetime.now().date())
    current_time = datetime.now().time() if is_today else None

    available = []
    for slot in doctor_slots:
        current = datetime.combine(date, slot.start_time)
        end = datetime.combine(date, slot.end_time)
        duration = timedelta(minutes=slot.slot_duration)

        while current + duration <= end:
            # Skip past slots if booking for today
            if is_today and current.time() <= current_time:
                current += duration
                continue

            time_str = current.strftime("%H:%M")
            display_str = current.strftime("%I:%M %p")

            # Count how many bookings exist at this exact time
            count_at_time = Appointment.objects.filter(
                doctor=doctor,
                appointment_date=date,
                appointment_time=current.time(),
            ).exclude(status="CANCELLED").count()

            is_available = count_at_time < slot.max_bookings

            available.append({
                "time": time_str,
                "display": display_str,
                "available": is_available,
                "booked": count_at_time,
                "max": slot.max_bookings,
            })
            current += duration

    return available


class AvailableSlotsAPIView(View):
    """AJAX endpoint returning available slots as JSON."""

    def get(self, request):
        doctor_id = request.GET.get("doctor")
        date_str = request.GET.get("date")

        if not doctor_id or not date_str:
            return JsonResponse({"slots": [], "error": "doctor and date are required"}, status=400)

        try:
            doctor = Doctor.objects.get(pk=doctor_id)
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except (Doctor.DoesNotExist, ValueError):
            return JsonResponse({"slots": [], "error": "Invalid doctor or date"}, status=400)

        slots = get_available_slots(doctor, date)
        return JsonResponse({"slots": slots, "doctor": doctor.name, "date": date_str})


class AppointmentListView(View):
    """List appointments with filter support and pagination."""

    def get(self, request):
        from django.core.paginator import Paginator

        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        qs = Appointment.objects.select_related("doctor", "patient").order_by(
            '-appointment_date', '-appointment_time'
        )

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

        total = qs.count()

        # Pagination — 15 per page
        paginator = Paginator(qs, 15)
        page_number = request.GET.get("page", 1)
        page_obj = paginator.get_page(page_number)

        # Build query string without 'page' for pagination links
        query_params = request.GET.copy()
        if 'page' in query_params:
            del query_params['page']
        filter_query = query_params.urlencode()

        context = {
            "appointments": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "filter_query": f"&{filter_query}" if filter_query else "",
            "doctors": Doctor.objects.filter(is_active=True),
            "status_choices": Appointment.STATUS_CHOICES,
            "selected_status": status or "",
            "selected_date": date_filter or "",
            "total": total,
        }
        return render(request, "dashboard/appointments/list.html", context)


class AppointmentCreateView(View):
    """Book a new appointment with slot validation."""

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
        from django.contrib import messages as django_messages

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

        # Parse date and time
        try:
            booking_date = datetime.strptime(apt_date, "%Y-%m-%d").date()
            booking_time = datetime.strptime(apt_time, "%H:%M").time()
        except (ValueError, TypeError):
            django_messages.error(request, "Invalid date or time format.")
            return redirect("/dashboard/appointments/book/")

        if booking_date < datetime.now().date():
            django_messages.error(request, "Cannot book appointments for past dates.")
            return redirect("/dashboard/appointments/book/")

        # ── Slot Validation ──
        matching_slot = DoctorSlot.objects.filter(
            doctor=doctor,
            schedule_date=booking_date,
            start_time__lte=booking_time,
            end_time__gt=booking_time,
            is_active=True,
        ).first()

        if not matching_slot:
            django_messages.error(
                request,
                f"Dr. {doctor.name} does not have a schedule slot at {apt_time} on {booking_date.strftime('%d %b %Y')}."
            )
            return redirect("/dashboard/appointments/book/")

        # ── Double-Booking Prevention (with row-level lock) ──
        with transaction.atomic():
            existing_count = (
                Appointment.objects
                .select_for_update()
                .filter(
                    doctor=doctor,
                    appointment_date=booking_date,
                    appointment_time=booking_time,
                )
                .exclude(status="CANCELLED")
                .count()
            )

            if existing_count >= matching_slot.max_bookings:
                django_messages.error(
                    request,
                    f"This slot is already fully booked ({matching_slot.max_bookings} booking(s) max)."
                )
                return redirect("/dashboard/appointments/book/")

            appointment = Appointment.objects.create(
                patient=patient,
                patient_name=patient_name,
                doctor=doctor,
                appointment_date=booking_date,
                appointment_time=booking_time,
                appointment_type=apt_type,
                notes=notes,
                fee=fee or 0,
                status="SCHEDULED",
            )

        # Log: Booking created
        log_activity(
            appointment, 'BOOKED', user=request.user,
            new_status='SCHEDULED',
            notes=f"Appointment booked with Dr. {doctor.name}",
        )

        django_messages.success(request, "Appointment booked successfully! Awaiting doctor confirmation.")
        return redirect("/dashboard/appointments/")


class AppointmentDetailView(View):
    """View/manage a single appointment."""

    def get(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk)
        activities = appointment.activities.select_related('performed_by').all()

        # Determine if the current user is the assigned doctor
        is_assigned_doctor = False
        if hasattr(request.user, 'doctor_profile') and request.user.doctor_profile:
            is_assigned_doctor = (request.user.doctor_profile.pk == appointment.doctor.pk)

        return render(request, "dashboard/appointments/detail.html", {
            "apt": appointment,
            "status_choices": Appointment.STATUS_CHOICES,
            "activities": activities,
            "is_assigned_doctor": is_assigned_doctor,
        })

    def post(self, request, pk):
        from django.contrib import messages as django_messages

        appointment = get_object_or_404(Appointment, pk=pk)
        action = request.POST.get("action")
        old_status = appointment.status

        if action == "confirm":
            appointment.status = "CONFIRMED"
            appointment.save()
            log_activity(
                appointment, 'CONFIRMED', user=request.user,
                old_status=old_status, new_status='CONFIRMED',
                notes="Doctor accepted the appointment",
            )

        elif action == "decline":
            reason = request.POST.get("reason", "").strip()
            appointment.status = "CANCELLED"
            appointment.cancellation_reason = reason
            appointment.save()
            log_activity(
                appointment, 'DECLINED', user=request.user,
                old_status=old_status, new_status='CANCELLED',
                notes=reason or "Doctor declined the appointment",
            )

        elif action == "check_in":
            appointment.check_in_time = now().time()
            appointment.status = "IN_PROGRESS"
            appointment.save()
            log_activity(
                appointment, 'CHECKED_IN', user=request.user,
                old_status=old_status, new_status='IN_PROGRESS',
                notes=f"Patient checked in at {appointment.check_in_time.strftime('%I:%M %p')}",
            )

        elif action == "check_out":
            appointment.check_out_time = now().time()
            appointment.status = "COMPLETED"
            appointment.save()
            log_activity(
                appointment, 'CHECKED_OUT', user=request.user,
                old_status=old_status, new_status='COMPLETED',
                notes=f"Patient checked out at {appointment.check_out_time.strftime('%I:%M %p')}",
            )

        elif action == "cancel":
            reason = request.POST.get("reason", "").strip()
            appointment.status = "CANCELLED"
            appointment.cancellation_reason = reason
            appointment.save()
            log_activity(
                appointment, 'CANCELLED', user=request.user,
                old_status=old_status, new_status='CANCELLED',
                notes=reason or "Appointment cancelled",
            )

        elif action == "update_status":
            new_status = request.POST.get("status", appointment.status)
            appointment.status = new_status
            if new_status == "NO_SHOW":
                appointment.no_show = True
            appointment.save()
            log_activity(
                appointment, 'STATUS_CHANGED', user=request.user,
                old_status=old_status, new_status=new_status,
                notes=f"Status changed from {old_status} to {new_status}",
            )

        return redirect(f"/dashboard/appointments/{pk}/")

