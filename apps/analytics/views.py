"""
Analytics & Reports views.
"""
from django.shortcuts import render, redirect
from django.views import View
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta
from apps.appointments.models import Appointment
from apps.billing.models import Invoice, Payment
from apps.clinical.models import Doctor
from apps.patients.models import Patient


class AnalyticsDashboardView(View):
    """Main Analytics Overview."""
    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        today = timezone.now().date()
        thirty_days_ago = today - timedelta(days=30)

        # Appointments metrics
        recent_apts = Appointment.objects.filter(appointment_date__gte=thirty_days_ago)
        total_apts = recent_apts.count()
        completed_apts = recent_apts.filter(status='COMPLETED').count()
        no_show_apts = recent_apts.filter(status='NO_SHOW').count()
        
        # Revenue metrics
        recent_invoices = Invoice.objects.filter(created_at__date__gte=thirty_days_ago)
        total_revenue = recent_invoices.filter(status__in=['PAID', 'PARTIALLY_PAID']).aggregate(
            total=Sum('grand_total')
        )['total'] or 0

        # Patient metrics
        new_patients = Patient.objects.filter(created_at__date__gte=thirty_days_ago).count()

        context = {
            "total_apts": total_apts,
            "completed_apts": completed_apts,
            "no_show_apts": no_show_apts,
            "no_show_rate": round((no_show_apts / total_apts * 100) if total_apts > 0 else 0, 1),
            "total_revenue": total_revenue,
            "new_patients": new_patients,
            "thirty_days_ago": thirty_days_ago,
            "today": today,
        }
        return render(request, "dashboard/analytics/index.html", context)


class RevenueAnalyticsView(View):
    """Detailed Revenue Reports."""
    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        # Quick breakdown
        payments = Payment.objects.values('method').annotate(total=Sum('amount'))
        
        context = {
            "payments_by_method": payments,
        }
        return render(request, "dashboard/analytics/revenue.html", context)


class AppointmentAnalyticsView(View):
    """Detailed Appointments Reports."""
    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        status_breakdown = Appointment.objects.values('status').annotate(count=Count('id'))
        type_breakdown = Appointment.objects.values('appointment_type').annotate(count=Count('id'))

        context = {
            "status_breakdown": status_breakdown,
            "type_breakdown": type_breakdown,
        }
        return render(request, "dashboard/analytics/appointments.html", context)


class DoctorAnalyticsView(View):
    """Doctor Performance Reports."""
    def get(self, request):
        tenant = getattr(request.user, "tenant", None)
        if not tenant:
            return redirect("/dashboard/")

        doctors = Doctor.objects.filter(is_active=True).annotate(
            total_apts=Count('appointments')
        )

        context = {
            "doctors": doctors,
        }
        return render(request, "dashboard/analytics/doctors.html", context)
