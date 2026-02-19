from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from django.db.models import Q

from .models import (
    Patient, Address, EmergencyContact,
    MedicalHistory, Allergy, Insurance, PatientDocument,
)
from .serializers import (
    PatientListSerializer, PatientDetailSerializer,
    PatientCreateUpdateSerializer,
    MedicalHistorySerializer, AllergySerializer,
    InsuranceSerializer, PatientDocumentSerializer,
)
from rest_framework.generics import RetrieveUpdateDestroyAPIView
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404

# ──────────────────────────────────────────────
# Patient List + Create
# ──────────────────────────────────────────────
class PatientListCreateAPIView(APIView):
    """
    GET  /api/patients/            → paginated, searchable list
    POST /api/patients/            → create a new patient
    """

    def get(self, request):
        patients = Patient.objects.all()

        # ── Search (name, phone, patient_id) ──
        search = request.query_params.get("search", "").strip()
        if search:
            patients = patients.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(patient_id__icontains=search)
                | Q(email__icontains=search)
            )

        # ── Filter by gender ──
        gender = request.query_params.get("gender")
        if gender:
            patients = patients.filter(gender=gender)

        # ── Filter by tag ──
        tag = request.query_params.get("tag")
        if tag:
            patients = patients.filter(tags__name__iexact=tag)

        # ── Filter by blood group ──
        blood_group = request.query_params.get("blood_group")
        if blood_group:
            patients = patients.filter(blood_group=blood_group)

        # ── Simple pagination ──
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = patients.count()
        patients = patients.prefetch_related("tags")[start:end]

        serializer = PatientListSerializer(patients, many=True)
        return Response({
            "count": total,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = PatientCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            patient = serializer.save()
            return Response(
                PatientDetailSerializer(patient).data,
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# Patient Detail / Update / Delete
# ──────────────────────────────────────────────
class PatientDetailAPIView(APIView):
    """
    GET    /api/patients/{id}/     → full patient profile
    PUT    /api/patients/{id}/     → update patient
    DELETE /api/patients/{id}/     → soft-delete patient
    """

    def _get_patient(self, pk):
        return get_object_or_404(Patient, pk=pk)

    def get(self, request, pk):
        patient = self._get_patient(pk)
        serializer = PatientDetailSerializer(patient)
        return Response(serializer.data)

    def put(self, request, pk):
        patient = self._get_patient(pk)
        serializer = PatientCreateUpdateSerializer(patient, data=request.data, partial=True)
        if serializer.is_valid():
            patient = serializer.save()
            return Response(PatientDetailSerializer(patient).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk):
        patient = self._get_patient(pk)
        patient.delete()  # soft delete via SoftDeleteMixin
        return Response(
            {"message": f"Patient {patient.patient_id} deleted successfully."},
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────
# Medical History (nested under patient)
# ──────────────────────────────────────────────
class MedicalHistoryListCreateAPIView(APIView):
    """
    GET  /api/patients/{patient_id}/medical-history/
    POST /api/patients/{patient_id}/medical-history/
    """

    def _get_patient(self, patient_pk):
        return get_object_or_404(Patient, pk=patient_pk)

    def get(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        records = patient.medical_history.all()
        serializer = MedicalHistorySerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        serializer = MedicalHistorySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# Allergies (nested under patient)
# ──────────────────────────────────────────────
class AllergyListCreateAPIView(APIView):
    """
    GET  /api/patients/{patient_id}/allergies/
    POST /api/patients/{patient_id}/allergies/
    """

    def _get_patient(self, patient_pk):
        return get_object_or_404(Patient, pk=patient_pk)

    def get(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        records = patient.allergies.all()
        serializer = AllergySerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        serializer = AllergySerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# Insurance (nested under patient)
# ──────────────────────────────────────────────
class InsuranceListCreateAPIView(APIView):
    """
    GET  /api/patients/{patient_id}/insurance/
    POST /api/patients/{patient_id}/insurance/
    """

    def _get_patient(self, patient_pk):
        return get_object_or_404(Patient, pk=patient_pk)

    def get(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        records = patient.insurance_policies.all()
        serializer = InsuranceSerializer(records, many=True)
        return Response(serializer.data)

    def post(self, request, patient_pk):
        patient = self._get_patient(patient_pk)
        serializer = InsuranceSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(patient=patient)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ──────────────────────────────────────────────
# Documents (nested under patient)
# ──────────────────────────────────────────────
from rest_framework.generics import ListCreateAPIView

class PatientDocumentListCreateAPIView(ListCreateAPIView):
    serializer_class = PatientDocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        patient = get_object_or_404(Patient, pk=self.kwargs["patient_pk"])
        queryset = patient.documents.all()

        doc_type = self.request.query_params.get("type")
        if doc_type:
            queryset = queryset.filter(document_type=doc_type)

        return queryset

    def perform_create(self, serializer):
        patient = get_object_or_404(Patient, pk=self.kwargs["patient_pk"])
        serializer.save(
            patient=patient,
            uploaded_by=self.request.user if self.request.user.is_authenticated else None,
        )



# ══════════════════════════════════════════════
# DETAIL VIEWS  (GET / PUT / DELETE per record)
# ══════════════════════════════════════════════

class MedicalHistoryDetailAPIView(APIView):
    """
    GET    /api/patients/{patient_id}/medical-history/{id}/
    PUT    /api/patients/{patient_id}/medical-history/{id}/
    DELETE /api/patients/{patient_id}/medical-history/{id}/  → hard delete
    """

    def _get_object(self, patient_pk, pk):
        return get_object_or_404(MedicalHistory, pk=pk, patient_id=patient_pk)

    def get(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        return Response(MedicalHistorySerializer(record).data)

    def put(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        serializer = MedicalHistorySerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        record.delete()
        return Response(
            {"message": "Medical history record deleted."},
            status=status.HTTP_200_OK,
        )


class AllergyDetailAPIView(APIView):
    """
    GET    /api/patients/{patient_id}/allergies/{id}/
    PUT    /api/patients/{patient_id}/allergies/{id}/
    DELETE /api/patients/{patient_id}/allergies/{id}/  → hard delete
    """

    def _get_object(self, patient_pk, pk):
        return get_object_or_404(Allergy, pk=pk, patient_id=patient_pk)

    def get(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        return Response(AllergySerializer(record).data)

    def put(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        serializer = AllergySerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        record.delete()
        return Response(
            {"message": "Allergy record deleted."},
            status=status.HTTP_200_OK,
        )


class InsuranceDetailAPIView(APIView):
    """
    GET    /api/patients/{patient_id}/insurance/{id}/
    PUT    /api/patients/{patient_id}/insurance/{id}/
    DELETE /api/patients/{patient_id}/insurance/{id}/  → hard delete
    """

    def _get_object(self, patient_pk, pk):
        return get_object_or_404(Insurance, pk=pk, patient_id=patient_pk)

    def get(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        return Response(InsuranceSerializer(record).data)

    def put(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        serializer = InsuranceSerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, patient_pk, pk):
        record = self._get_object(patient_pk, pk)
        record.delete()
        return Response(
            {"message": "Insurance record deleted."},
            status=status.HTTP_200_OK,
        )


class PatientDocumentDetailAPIView(RetrieveUpdateDestroyAPIView):
    """
    GET    /api/patients/{patient_pk}/documents/{pk}/
    PUT    /api/patients/{patient_pk}/documents/{pk}/
    DELETE /api/patients/{patient_pk}/documents/{pk}/
    """
    serializer_class = PatientDocumentSerializer
    parser_classes = [MultiPartParser, FormParser]

    def get_queryset(self):
        return PatientDocument.objects.filter(
            patient__pk=self.kwargs["patient_pk"]
        )

