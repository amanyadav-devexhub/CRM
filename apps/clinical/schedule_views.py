"""
Schedule CRUD views — manage DoctorSlot working hours.
"""
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from apps.clinical.models import Doctor, DoctorSlot


class ScheduleListView(View):
    """List all doctor schedules grouped by doctor."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        doctors = Doctor.objects.filter(is_active=True).prefetch_related("slots")
        selected_doctor_id = request.GET.get("doctor")

        schedule_data = []
        for doc in doctors:
            slots = doc.slots.filter(
                is_active=True, schedule_date__gte=date.today()
            ).order_by("schedule_date", "start_time")
            if selected_doctor_id and str(doc.pk) != selected_doctor_id:
                continue
            schedule_data.append({
                "doctor": doc,
                "slots": slots,
                "slot_count": slots.count(),
            })

        return render(request, "dashboard/schedules/list.html", {
            "schedule_data": schedule_data,
            "doctors": doctors,
            "selected_doctor": selected_doctor_id or "",
            "total_slots": DoctorSlot.objects.filter(
                is_active=True, schedule_date__gte=date.today()
            ).count(),
            "today": date.today().isoformat(),
        })


class ScheduleCreateView(View):
    """Create a new DoctorSlot."""

    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        return render(request, "dashboard/schedules/form.html", {
            "doctors": Doctor.objects.filter(is_active=True),
            "editing": False,
            "today": date.today().isoformat(),
        })

    def post(self, request):
        doctor_id = request.POST.get("doctor")
        schedule_date = request.POST.get("schedule_date")
        start_time = request.POST.get("start_time")
        end_time = request.POST.get("end_time")
        slot_duration = request.POST.get("slot_duration", 15)
        max_bookings = request.POST.get("max_bookings", 1)

        doctor = get_object_or_404(Doctor, pk=doctor_id)

        # Block past dates
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(schedule_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return redirect("/schedules/create/")

        if parsed_date < date.today():
            messages.error(request, "Cannot create schedules for past dates.")
            return redirect("/schedules/create/")

        # Check for overlapping slots on the same date
        existing = DoctorSlot.objects.filter(
            doctor=doctor,
            schedule_date=parsed_date,
            is_active=True,
        ).filter(
            start_time__lt=end_time,
            end_time__gt=start_time,
        )
        if existing.exists():
            messages.error(request, "This time range overlaps with an existing slot for this doctor on this date.")
            return redirect("/schedules/create/")

        DoctorSlot.objects.create(
            doctor=doctor,
            schedule_date=parsed_date,
            start_time=start_time,
            end_time=end_time,
            slot_duration=int(slot_duration),
            max_bookings=int(max_bookings),
        )
        messages.success(request, f"Schedule slot added for Dr. {doctor.name} on {parsed_date.strftime('%d %b %Y')}.")
        return redirect("/schedules/")


class ScheduleEditView(View):
    """Edit an existing DoctorSlot."""

    def get(self, request, pk):
        slot = get_object_or_404(DoctorSlot, pk=pk)
        return render(request, "dashboard/schedules/form.html", {
            "doctors": Doctor.objects.filter(is_active=True),
            "slot": slot,
            "editing": True,
            "today": date.today().isoformat(),
        })

    def post(self, request, pk):
        slot = get_object_or_404(DoctorSlot, pk=pk)

        new_date = request.POST.get("schedule_date")
        from datetime import datetime
        try:
            parsed_date = datetime.strptime(new_date, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format.")
            return redirect(f"/schedules/{pk}/edit/")

        if parsed_date < date.today():
            messages.error(request, "Cannot set schedule to a past date.")
            return redirect(f"/schedules/{pk}/edit/")

        slot.schedule_date = parsed_date
        slot.start_time = request.POST.get("start_time", slot.start_time)
        slot.end_time = request.POST.get("end_time", slot.end_time)
        slot.slot_duration = int(request.POST.get("slot_duration", slot.slot_duration))
        slot.max_bookings = int(request.POST.get("max_bookings", slot.max_bookings))

        # Check for overlapping slots (exclude self)
        existing = DoctorSlot.objects.filter(
            doctor=slot.doctor,
            schedule_date=slot.schedule_date,
            is_active=True,
        ).exclude(pk=slot.pk).filter(
            start_time__lt=slot.end_time,
            end_time__gt=slot.start_time,
        )
        if existing.exists():
            messages.error(request, "This time range overlaps with an existing slot.")
            return redirect(f"/schedules/{pk}/edit/")

        slot.save()
        messages.success(request, f"Schedule updated for Dr. {slot.doctor.name}.")
        return redirect("/schedules/")


class ScheduleDeleteView(View):
    """Delete (deactivate) a DoctorSlot."""

    def post(self, request, pk):
        slot = get_object_or_404(DoctorSlot, pk=pk)
        slot.is_active = False
        slot.save()
        messages.success(request, f"Schedule slot removed for Dr. {slot.doctor.name}.")
        return redirect("/schedules/")
