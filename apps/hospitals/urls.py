from django.urls import path
from .template_views import (
    CategoryHospitalsView, BedManagementView, AdmissionListView,
    ERConsoleView, PatientMonitoringView, StaffingView,
    WardManagementView, InsuranceTrackingView, OPDToIPDAdmissionView,
    DischargeAndBillView, DepartmentManagementView, HospitalPatientsView
)

urlpatterns = [
    path('', CategoryHospitalsView.as_view(), name='category-hospitals'),
    path('departments/', DepartmentManagementView.as_view(), name='hospital-departments'),
    path('wards/', WardManagementView.as_view(), name='hospital-wards'),
    path('beds/', BedManagementView.as_view(), name='hospital-beds'),
    path('patients/', HospitalPatientsView.as_view(), name='hospital-patients'),
    path('admissions/', AdmissionListView.as_view(), name='hospital-admissions'),
    path('er/', ERConsoleView.as_view(), name='hospital-er-console'),
    path('monitoring/<uuid:admission_id>/', PatientMonitoringView.as_view(), name='patient-monitoring'),
    path('staffing/', StaffingView.as_view(), name='hospital-staffing'),
    path('insurance/', InsuranceTrackingView.as_view(), name='hospital-insurance'),
    path('admit-opd/<uuid:patient_id>/', OPDToIPDAdmissionView.as_view(), name='hospital-opd-to-ipd'),
    path('discharge/<uuid:admission_id>/', DischargeAndBillView.as_view(), name='hospital-discharge'),
]
