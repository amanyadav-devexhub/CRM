"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from apps.tenants.views import AdminDashboardView, SubAdminDashboardView, ClinicSettingsView
from apps.patients.template_views import (
    PatientListView, PatientDetailView,
    PatientCreateView, PatientEditView, PatientDeleteView,
)
from apps.tenants.template_views import (
    TenantCreatePageView,
    CategoryIndexView, CategoryClinicView, CategoryPharmacyView,
    CategoryListView,
    PharmacyInventoryView, PharmacySalesView, PharmacyPrescriptionsView,
    ClinicDoctorsView, ClinicAppointmentsView, ClinicPatientsView,
    ClinicDashboardAPIView,CategoryLabsView
)
from apps.communications.template_views import (
    CommunicationsIndexView, MessageListView,
    CampaignListView, FeedbackListView,
)
from apps.notifications.template_views import NotificationCenterView
from apps.accounts.public_views import LandingPageView
from apps.accounts.auth_views import (
    RegisterView, OTPVerifyView, ResendOTPView,
    LoginView, LogoutView,
)
from apps.accounts.jwt_views import (
    JWTTokenObtainView, JWTTokenRefreshView, JWTTokenVerifyView,
)
from apps.accounts.onboarding_views import (
    OnboardingStep1View, OnboardingStep2View, OnboardingStep3View,
)
from apps.accounts.staff_views import (
    StaffListView, StaffCreateView, StaffEditView, StaffDeleteView,
    DoctorListView,
)
from apps.appointments.views import (
    AppointmentListView, AppointmentCreateView, AppointmentDetailView,
)
from apps.billing.views import (
    BillingListView, BillingCreateView, BillingDetailView,
)
from apps.clinical.views import (
    ClinicalNoteListView, ClinicalNoteCreateView, 
    PrescriptionListView, PrescriptionCreateView,
)
from apps.analytics.views import (
    AnalyticsDashboardView, RevenueAnalyticsView,
    AppointmentAnalyticsView, DoctorAnalyticsView,
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # ── Public / Auth ──
    path("", LandingPageView.as_view(), name="landing"),
    path("login/", LoginView.as_view(), name="login"),
    path("register/", RegisterView.as_view(), name="register"),
    path("verify-otp/", OTPVerifyView.as_view(), name="verify-otp"),
    path("resend-otp/", ResendOTPView.as_view(), name="resend-otp"),
    path("logout/", LogoutView.as_view(), name="logout"),

    # ── Password Reset ──
    path("password-reset/", auth_views.PasswordResetView.as_view(
        template_name="accounts/password_reset.html",
        email_template_name="accounts/password_reset_email.html",
        subject_template_name="accounts/password_reset_subject.txt",
        success_url="/password-reset/done/",
    ), name="password_reset"),
    path("password-reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="accounts/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="accounts/password_reset_confirm.html",
        success_url="/password-reset/complete/",
    ), name="password_reset_confirm"),
    path("password-reset/complete/", auth_views.PasswordResetCompleteView.as_view(
        template_name="accounts/password_reset_complete.html",
    ), name="password_reset_complete"),

    # ── Onboarding Wizard ──
    path("onboarding/", OnboardingStep1View.as_view(), name="onboarding-step1"),
    path("onboarding/plan/", OnboardingStep2View.as_view(), name="onboarding-step2"),
    path("onboarding/confirm/", OnboardingStep3View.as_view(), name="onboarding-step3"),

    # ── API endpoints ──
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/communications/", include("apps.communications.urls")),
    path("api/notifications/", include("apps.notifications.urls")),

    # ── JWT Auth Endpoints (programmatic API access) ──
    path("api/auth/token/", JWTTokenObtainView.as_view(), name="token-obtain"),
    path("api/auth/token/refresh/", JWTTokenRefreshView.as_view(), name="token-refresh"),
    path("api/auth/token/verify/", JWTTokenVerifyView.as_view(), name="token-verify"),

    # ── Admin Dashboard (Platform Owner / SuperAdmin) ──
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),

    # ── Sub-Admin Dashboard (Tenant / Clinic) ──
    path("dashboard/", SubAdminDashboardView.as_view(), name="dashboard"),
    path("dashboard/settings/", ClinicSettingsView.as_view(), name="clinic-settings"),

    # ── Staff / Employee CRUD ──
    path("dashboard/staff/", StaffListView.as_view(), name="staff-list"),
    path("dashboard/staff/create/", StaffCreateView.as_view(), name="staff-create"),
    path("dashboard/staff/<uuid:pk>/edit/", StaffEditView.as_view(), name="staff-edit"),
    path("dashboard/staff/<uuid:pk>/delete/", StaffDeleteView.as_view(), name="staff-delete"),

    # ── Doctors ──
    path("dashboard/doctors/", DoctorListView.as_view(), name="doctor-list"),

    # ── Appointments ──
    path("dashboard/appointments/", AppointmentListView.as_view(), name="appointment-list"),
    path("dashboard/appointments/book/", AppointmentCreateView.as_view(), name="appointment-create"),
    path("dashboard/appointments/<uuid:pk>/", AppointmentDetailView.as_view(), name="appointment-detail"),

    # ── Billing ──
    path("dashboard/billing/", BillingListView.as_view(), name="billing-list"),
    path("dashboard/billing/create/", BillingCreateView.as_view(), name="billing-create"),
    path("dashboard/billing/<uuid:pk>/", BillingDetailView.as_view(), name="billing-detail"),

    # ── Clinical Notes & Prescriptions ──
    path("dashboard/clinical/notes/", ClinicalNoteListView.as_view(), name="note-list"),
    path("dashboard/clinical/notes/create/", ClinicalNoteCreateView.as_view(), name="note-create"),
    path("dashboard/clinical/prescriptions/", PrescriptionListView.as_view(), name="prescription-list"),
    path("dashboard/clinical/prescriptions/create/", PrescriptionCreateView.as_view(), name="prescription-create"),
    path("dashboard/clinical/prescriptions/<uuid:pk>/pdf/", PrescriptionCreateView.as_view(), name="prescription-pdf"), # Placeholder for now

    # ── Analytics & Reports ──
    path("dashboard/analytics/", AnalyticsDashboardView.as_view(), name="analytics-dashboard"),
    path("dashboard/analytics/revenue/", RevenueAnalyticsView.as_view(), name="analytics-revenue"),
    path("dashboard/analytics/appointments/", AppointmentAnalyticsView.as_view(), name="analytics-appointments"),
    path("dashboard/analytics/doctors/", DoctorAnalyticsView.as_view(), name="analytics-doctors"),

    # ── Patient HTML pages ──
    path("patients/", PatientListView.as_view(), name="patient-list"),
    path("patients/create/", PatientCreateView.as_view(), name="patient-create"),
    path("patients/<uuid:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<uuid:pk>/edit/", PatientEditView.as_view(), name="patient-edit"),
    path("patients/<uuid:pk>/delete/", PatientDeleteView.as_view(), name="patient-delete"),

    # ── Tenant HTML pages ──
    path("tenants/create/", TenantCreatePageView.as_view(), name="tenant-create-page"),

    # ── Category Lists (Super Admin) ──
    path("categories/list/<slug:category_slug>/", CategoryListView.as_view(), name="category-list"),

    # ── Category Pages (standalone management hubs) ──
    path("categories/", CategoryIndexView.as_view(), name="category-index"),

    # Clinic Flow
    path("categories/clinic/", CategoryClinicView.as_view(), name="category-clinic"),
    path("categories/clinic/doctors/", ClinicDoctorsView.as_view(), name="clinic-doctors"),
    path("categories/clinic/appointments/", ClinicAppointmentsView.as_view(), name="clinic-appointments"),
    path("categories/clinic/patients/", ClinicPatientsView.as_view(), name="clinic-patients"),
    path("categories/clinic/api/stats/", ClinicDashboardAPIView.as_view(), name="clinic-api-stats"),

    # Hospital Flow
    path("categories/hospital/", include("apps.hospitals.urls")),
    path("categories/pharmacy/", CategoryPharmacyView.as_view(), name="category-pharmacy"),
    path("categories/pharmacy/inventory/", PharmacyInventoryView.as_view(), name="pharmacy-inventory"),
    path("categories/pharmacy/sales/", PharmacySalesView.as_view(), name="pharmacy-sales"),
    path("categories/pharmacy/prescriptions/", PharmacyPrescriptionsView.as_view(), name="pharmacy-prescriptions"),
    path("categories/labs/", CategoryLabsView.as_view(), name="category-labs"),

    # ── Communications HTML pages ──
    path("communications/", CommunicationsIndexView.as_view(), name="communications-index"),
    path("communications/messages/", MessageListView.as_view(), name="communications-messages"),
    path("communications/campaigns/", CampaignListView.as_view(), name="communications-campaigns"),
    path("communications/feedback/", FeedbackListView.as_view(), name="communications-feedback"),

    # ── Notifications HTML pages ──
    path("notifications/", NotificationCenterView.as_view(), name="notification-center"),
]
