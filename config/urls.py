"""
URL configuration for config project.
"""

from django.contrib import admin
from django.urls import path, include
from apps.tenants.views import AdminDashboardView, SubAdminDashboardView
from apps.patients.template_views import (
    PatientListView, PatientDetailView,
    PatientCreateView, PatientEditView, PatientDeleteView,
)
from apps.tenants.template_views import (
    TenantCreatePageView,
    CategoryIndexView, CategoryClinicView, CategoryPharmacyView,
    CategoryHospitalsView, CategoryLabsView, CategoryListView,
    PharmacyInventoryView, PharmacySalesView, PharmacyPrescriptionsView,
    ClinicDoctorsView, ClinicAppointmentsView, ClinicPatientsView,
    ClinicDashboardAPIView,
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
from apps.accounts.onboarding_views import (
    OnboardingStep1View, OnboardingStep2View, OnboardingStep3View,
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

    # ── Onboarding Wizard ──
    path("onboarding/", OnboardingStep1View.as_view(), name="onboarding-step1"),
    path("onboarding/plan/", OnboardingStep2View.as_view(), name="onboarding-step2"),
    path("onboarding/confirm/", OnboardingStep3View.as_view(), name="onboarding-step3"),

    # ── API endpoints ──
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/patients/", include("apps.patients.urls")),
    path("api/communications/", include("apps.communications.urls")),
    path("api/notifications/", include("apps.notifications.urls")),

    # ── Admin Dashboard (Platform Owner / SuperAdmin) ──
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),

    # ── Sub-Admin Dashboard (Tenant / Clinic) ──
    path("dashboard/", SubAdminDashboardView.as_view(), name="dashboard"),

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

    # Pharmacy Flow
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
