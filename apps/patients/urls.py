from django.urls import path
from .views import (
    PatientListCreateAPIView,
    PatientDetailAPIView,
    MedicalHistoryListCreateAPIView,
    MedicalHistoryDetailAPIView,
    AllergyListCreateAPIView,
    AllergyDetailAPIView,
    InsuranceListCreateAPIView,
    InsuranceDetailAPIView,
    PatientDocumentListCreateAPIView,
    PatientDocumentDetailAPIView,
)

urlpatterns = [
    # Patient CRUD
    path("", PatientListCreateAPIView.as_view(), name="patient-list-create"),
    path("<uuid:pk>/", PatientDetailAPIView.as_view(), name="patient-detail"),

    # Medical History — list/create + detail/update/delete
    path(
        "<uuid:patient_pk>/medical-history/",
        MedicalHistoryListCreateAPIView.as_view(),
        name="patient-medical-history",
    ),
    path(
        "<uuid:patient_pk>/medical-history/<uuid:pk>/",
        MedicalHistoryDetailAPIView.as_view(),
        name="patient-medical-history-detail",
    ),

    # Allergies — list/create + detail/update/delete
    path(
        "<uuid:patient_pk>/allergies/",
        AllergyListCreateAPIView.as_view(),
        name="patient-allergies",
    ),
    path(
        "<uuid:patient_pk>/allergies/<uuid:pk>/",
        AllergyDetailAPIView.as_view(),
        name="patient-allergy-detail",
    ),

    # Insurance — list/create + detail/update/delete
    path(
        "<uuid:patient_pk>/insurance/",
        InsuranceListCreateAPIView.as_view(),
        name="patient-insurance",
    ),
    path(
        "<uuid:patient_pk>/insurance/<uuid:pk>/",
        InsuranceDetailAPIView.as_view(),
        name="patient-insurance-detail",
    ),

    # Documents — list/create + detail/update/delete
    path(
        "<uuid:patient_pk>/documents/",
        PatientDocumentListCreateAPIView.as_view(),
        name="patient-documents",
    ),
    path(
        "<uuid:patient_pk>/documents/<uuid:pk>/",
        PatientDocumentDetailAPIView.as_view(),
        name="patient-document-detail",
    ),
]
