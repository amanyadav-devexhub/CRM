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
)

urlpatterns = [
    path("admin/", admin.site.urls),

    # API endpoints
    path("api/tenants/", include("apps.tenants.urls")),
    path("api/patients/", include("apps.patients.urls")),

    # Admin Dashboard (Platform Owner)
    path("admin-dashboard/", AdminDashboardView.as_view(), name="admin-dashboard"),

    # Sub-Admin Dashboard (Tenant / Clinic)
    path("dashboard/", SubAdminDashboardView.as_view(), name="dashboard"),

    # Patient HTML pages
    path("patients/", PatientListView.as_view(), name="patient-list"),
    path("patients/create/", PatientCreateView.as_view(), name="patient-create"),
    path("patients/<uuid:pk>/", PatientDetailView.as_view(), name="patient-detail"),
    path("patients/<uuid:pk>/edit/", PatientEditView.as_view(), name="patient-edit"),
    path("patients/<uuid:pk>/delete/", PatientDeleteView.as_view(), name="patient-delete"),

    # Tenant HTML pages
    path("tenants/create/", TenantCreatePageView.as_view(), name="tenant-create-page"),

    # Category Lists (Super Admin)
    path("admin/category/<slug:category_slug>/", CategoryListView.as_view(), name="category-list"),

    # Category Pages (standalone management hubs)
    path("categories/", CategoryIndexView.as_view(), name="category-index"),
    path("categories/clinic/", CategoryClinicView.as_view(), name="category-clinic"),
    # Pharmacy Flow
    path("categories/pharmacy/", CategoryPharmacyView.as_view(), name="category-pharmacy"),
    path("categories/pharmacy/inventory/", PharmacyInventoryView.as_view(), name="pharmacy-inventory"),
    path("categories/pharmacy/sales/", PharmacySalesView.as_view(), name="pharmacy-sales"),
    path("categories/pharmacy/prescriptions/", PharmacyPrescriptionsView.as_view(), name="pharmacy-prescriptions"),
    path("categories/labs/", CategoryLabsView.as_view(), name="category-labs"),
]

