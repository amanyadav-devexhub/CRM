from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.utils import timezone
from django.db import models
from django.db.models import Count, Sum
from .models import Department, Bed, Admission, ERCase, PatientVital, StaffShift, Hospital, Ward, CorporateAccount, InsuranceClaim, HospitalStaff
from apps.patients.models import Patient
from apps.clinical.models import Doctor

class HospitalSetupMixin:
    """Ensure a hospital profile exists."""
    def get_hospital(self):
        h = Hospital.objects.first()
        if not h:
            h = Hospital.objects.create(name="Central Enterprise Hospital", license_number="ENT-999-001")
        return h

class CategoryHospitalsView(HospitalSetupMixin, View):
    """Enterprise Executive Dashboard."""
    def get(self, request):
        hospital = self.get_hospital()
        departments = Department.objects.annotate(
            total_beds=Count('beds'),
            occupied_beds=Count('beds', filter=models.Q(beds__status='OCCUPIED'))
        )
        
        # IPD Stats
        total_admissions = Admission.objects.exclude(status='DISCHARGED').count()
        critical_patients = Admission.objects.filter(status='CRITICAL').count()
        
        # Lab Integration (Mock or real if available)
        try:
            from apps.labs.models import LabOrder
            pending_lab_reports = LabOrder.objects.filter(status='PENDING').count()
        except ImportError:
            pending_lab_reports = 0
            
        # Pharmacy Integration
        try:
            from apps.pharmacy.models import Medicine
            low_stock_alerts = Medicine.objects.filter(stock__lt=10).count()
        except ImportError:
            low_stock_alerts = 0
            
        # Billing Integration (Insurance)
        pending_claims = InsuranceClaim.objects.filter(status='PENDING').count()
        
        context = {
            'hospital': hospital,
            'departments': departments,
            'total_admissions': total_admissions,
            'critical_patients': critical_patients,
            'pending_lab_reports': pending_lab_reports,
            'low_stock_alerts': low_stock_alerts,
            'pending_claims': pending_claims,
            'recent_cases': ERCase.objects.all().order_by('-arrival_time')[:5],
        }
        return render(request, 'categories/hospital_enterprise_dashboard.html', context)

class HospitalPatientsView(HospitalSetupMixin, View):
    """Patient management within the hospital."""
    template_name = "categories/hospital_patients.html"
    
    BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

    def get(self, request):
        from apps.patients.models import Patient
        from django.db.models import Q
        
        patients = Patient.objects.all().prefetch_related('admissions')

        search = request.GET.get('search', '').strip()
        gender = request.GET.get('gender', '').strip()
        blood = request.GET.get('blood_group', '').strip()

        if search:
            patients = patients.filter(
                Q(first_name__icontains=search)
                | Q(last_name__icontains=search)
                | Q(phone__icontains=search)
                | Q(patient_id__icontains=search)
                | Q(email__icontains=search)
            )
        if gender:
            patients = patients.filter(gender=gender)
        if blood:
            patients = patients.filter(blood_group=blood)

        context = {
            "patients": patients,
            "blood_groups": self.BLOOD_GROUPS,
            "search_query": search,
            "gender_filter": gender,
            "blood_filter": blood,
            "success_message": request.GET.get('success', ''),
            "error_message": request.GET.get('error', ''),
        }
        return render(request, self.template_name, context)

    def post(self, request):
        from apps.patients.models import Patient
        from django.shortcuts import redirect

        try:
            patient = Patient.objects.create(
                first_name=request.POST.get('first_name', '').strip(),
                last_name=request.POST.get('last_name', '').strip(),
                date_of_birth=request.POST.get('date_of_birth') or None,
                gender=request.POST.get('gender', ''),
                blood_group=request.POST.get('blood_group', ''),
                phone=request.POST.get('phone', '').strip(),
                email=request.POST.get('email', '').strip(),
                notes=request.POST.get('notes', '').strip(),
            )
            msg = f"Successfully registered {patient.full_name} ({patient.patient_id})"
            return redirect(f"{request.path}?success={msg}")
        except Exception as e:
            patients = Patient.objects.all().prefetch_related('admissions')
            return render(request, self.template_name, {
                "patients": patients,
                "blood_groups": self.BLOOD_GROUPS,
                "error_message": str(e),
            })

class DepartmentManagementView(HospitalSetupMixin, View):
    """Manage Hospital Departments."""
    def get(self, request):
        departments = Department.objects.annotate(
            total_beds=Count('beds'),
            occupied_beds=Count('beds', filter=models.Q(beds__status='OCCUPIED'))
        ).select_related('head_of_department')
        doctors = Doctor.objects.all()
        
        context = {
            'hospital': self.get_hospital(),
            'departments': departments,
            'doctors': doctors,
        }
        return render(request, 'categories/hospital_departments.html', context)

    def post(self, request):
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        head_id = request.POST.get('head_of_department')
        revenue_tracking = request.POST.get('revenue_tracking') == 'on'

        Department.objects.create(
            hospital=self.get_hospital(),
            name=name,
            description=description,
            head_of_department_id=head_id if head_id else None,
            revenue_tracking=revenue_tracking
        )
        return redirect('hospital-departments')

class WardManagementView(HospitalSetupMixin, View):
    """Manage Wards and Bed hierarchy."""
    def get(self, request):
        wards = Ward.objects.all().select_related('department').annotate(
            total_beds=Count('beds'),
            occupied_beds=Count('beds', filter=models.Q(beds__status='OCCUPIED'))
        )
        departments = Department.objects.all()
        context = {
            'hospital': self.get_hospital(),
            'wards': wards,
            'departments': departments,
        }
        return render(request, 'categories/hospital_wards.html', context)

    def post(self, request):
        name = request.POST.get('name')
        dept_id = request.POST.get('department_id')
        ward_type = request.POST.get('ward_type')
        Ward.objects.create(name=name, department_id=dept_id, ward_type=ward_type)
        return redirect('hospital-wards')

class InsuranceTrackingView(HospitalSetupMixin, View):
    """Manage Insurance claims and Corporate accounts."""
    def get(self, request):
        claims = InsuranceClaim.objects.all().select_related('admission__patient', 'corporate_account')
        corporate_accounts = CorporateAccount.objects.all()
        context = {
            'hospital': self.get_hospital(),
            'claims': claims,
            'corporate_accounts': corporate_accounts,
            'admissions': Admission.objects.filter(status='ACTIVE'),
        }
        return render(request, 'categories/hospital_insurance.html', context)

    def post(self, request):
        if 'create_claim' in request.POST:
            adm_id = request.POST.get('admission_id')
            corp_id = request.POST.get('corporate_account_id')
            policy = request.POST.get('policy_number', '')
            amount = request.POST.get('requested_amount')
            
            if adm_id and corp_id:
                InsuranceClaim.objects.create(
                    admission_id=adm_id,
                    corporate_account_id=corp_id,
                    policy_number=policy,
                    requested_amount=amount if amount else 0
                )
        else:
            # Add corporate account
            name = request.POST.get('name')
            credit = request.POST.get('credit_limit')
            if name:
                CorporateAccount.objects.create(name=name, credit_limit=credit if credit else 0)
        return redirect('hospital-insurance')

class OPDToIPDAdmissionView(HospitalSetupMixin, View):
    """Convert an OPD patient (Clinic) to an IPD admission."""
    def post(self, request, patient_id):
        patient = get_object_or_404(Patient, id=patient_id)
        dept_id = request.POST.get('department_id')
        doctor_id = request.POST.get('doctor_id')
        bed_id = request.POST.get('bed_id')
        
        # Create admission
        admission = Admission.objects.create(
            patient=patient,
            department_id=dept_id if dept_id else None,
            attending_doctor_id=doctor_id if doctor_id else None,
            bed_id=bed_id if bed_id else None,
            status='ACTIVE'
        )
        
        # Update bed status
        if bed_id:
            Bed.objects.filter(id=bed_id).update(status='OCCUPIED')
            
        return redirect('hospital-admissions')

class BedManagementView(View):
    """View and manage beds."""
    def get(self, request):
        beds = Bed.objects.all().select_related('department')
        departments = Department.objects.all()
        context = {
            'beds': beds,
            'departments': departments,
        }
        return render(request, 'categories/hospital_beds.html', context)

    def post(self, request):
        # Handle adding a new bed
        bed_number = request.POST.get('bed_number')
        bed_type = request.POST.get('bed_type')
        dept_id = request.POST.get('department_id')
        price = request.POST.get('price', 0)
        
        dept = get_object_or_404(Department, id=dept_id)
        Bed.objects.create(
            bed_number=bed_number,
            bed_type=bed_type,
            department=dept,
            price_per_day=price
        )
        return redirect('hospital-beds')

class AdmissionListView(View):
    """Manage admissions."""
    def get(self, request):
        admissions = Admission.objects.all().select_related('patient', 'bed', 'department')
        patients = Patient.objects.all()
        beds = Bed.objects.filter(status='AVAILABLE')
        departments = Department.objects.all()
        doctors = Doctor.objects.all()
        
        context = {
            'admissions': admissions,
            'patients': patients,
            'available_beds': beds,
            'departments': departments,
            'doctors': doctors,
        }
        return render(request, 'categories/hospital_admissions.html', context)

    def post(self, request):
        # Handle new admission
        patient_id = request.POST.get('patient_id')
        bed_id = request.POST.get('bed_id')
        reason = request.POST.get('reason')
        doctor_id = request.POST.get('doctor_id')
        
        patient = get_object_or_404(Patient, id=patient_id)
        bed = get_object_or_404(Bed, id=bed_id)
        doctor = get_object_or_404(Doctor, id=doctor_id)
        
        admission = Admission.objects.create(
            patient=patient,
            bed=bed,
            department=bed.department,
            notes=reason,
            attending_doctor=doctor,
            status='ACTIVE'
        )
        
        # Update bed status
        bed.status = 'OCCUPIED'
        bed.save()
        
        return redirect('hospital-admissions')

class ERConsoleView(View):
    """Emergency Room dashboard."""
    def get(self, request):
        cases = ERCase.objects.exclude(status__in=['ADMITTED', 'DISCHARGED'])
        doctors = Doctor.objects.all()
        context = {
            'er_cases': cases,
            'doctors': doctors,
            'triage_choices': ERCase.TRIAGE_LEVELS,
        }
        return render(request, 'categories/hospital_er_console.html', context)

    def post(self, request):
        # Handle new ER arrival
        name = request.POST.get('patient_name')
        triage = request.POST.get('triage_level')
        complaint = request.POST.get('complaint')
        
        ERCase.objects.create(
            patient_name=name,
            triage_level=triage,
            chief_complaint=complaint,
            status='TRIAGE_PENDING'
        )
        return redirect('hospital-er-console')

class PatientMonitoringView(HospitalSetupMixin, View):
    """Refined Patient Monitoring with Lab/Pharmacy integration."""
    def get(self, request, admission_id):
        admission = get_object_or_404(Admission, id=admission_id)
        vitals = PatientVital.objects.filter(admission=admission).order_by('-recorded_at')
        
        # Cross-app data: Labs
        lab_orders = []
        try:
            from apps.labs.models import LabOrder
            lab_orders = LabOrder.objects.filter(patient=admission.patient).order_by('-ordered_at')[:5]
        except ImportError:
            pass

        # Cross-app data: Pharmacy
        prescriptions = []
        try:
            from apps.pharmacy.models import Prescription
            # Match by patient name or custom ID if available
            prescriptions = Prescription.objects.filter(patient_name=admission.patient.full_name).order_by('-created_at')[:5]
        except ImportError:
            pass

        context = {
            'hospital': self.get_hospital(),
            'admission': admission,
            'vitals': vitals,
            'lab_orders': lab_orders,
            'prescriptions': prescriptions,
            'doctors': Doctor.objects.all(),
        }
        return render(request, 'categories/hospital_monitoring.html', context)

    def post(self, request, admission_id):
        # Save new vitals
        admission = get_object_or_404(Admission, id=admission_id)
        
        temp = request.POST.get('temp')
        pulse = request.POST.get('pulse')
        sbp = request.POST.get('sbp')
        dbp = request.POST.get('dbp')
        spo2 = request.POST.get('spo2')
        doc_id = request.POST.get('doctor_id')

        PatientVital.objects.create(
            admission=admission,
            temperature=temp if temp else None,
            pulse=pulse if pulse else None,
            systolic_bp=sbp if sbp else None,
            diastolic_bp=dbp if dbp else None,
            spo2=spo2 if spo2 else None,
            recorded_by_id=doc_id if doc_id else None
        )
        return redirect('patient-monitoring', admission_id=admission_id)

class StaffingView(View):
    """Duty roster management."""
    def get(self, request):
        shifts = StaffShift.objects.all().select_related('doctor', 'department')
        doctors = Doctor.objects.all()
        departments = Department.objects.all()
        staff_members = HospitalStaff.objects.all()
        
        context = {
            'shifts': shifts,
            'doctors': doctors,
            'staff_members': staff_members,
            'departments': departments,
            'shift_types': StaffShift.SHIFT_TYPES,
            'staff_roles': HospitalStaff.ROLE_CHOICES,
            'doctor_specializations': Doctor.SPECIALIZATION_CHOICES,
        }
        return render(request, 'categories/hospital_staffing.html', context)

    def post(self, request):
        if 'create_doctor' in request.POST:
            name = request.POST.get('name')
            specialization = request.POST.get('specialization')
            phone = request.POST.get('phone', '')
            email = request.POST.get('email', '')
            
            Doctor.objects.create(
                name=name,
                specialization=specialization,
                phone=phone,
                email=email
            )
        elif 'create_staff' in request.POST:
            name = request.POST.get('name')
            role = request.POST.get('role')
            dept_id = request.POST.get('department_id')
            phone = request.POST.get('phone', '')
            
            HospitalStaff.objects.create(
                name=name,
                role=role,
                department_id=dept_id if dept_id else None,
                phone=phone
            )
        else:
            doctor_id = request.POST.get('doctor_id')
            staff_id = request.POST.get('staff_id')
            dept_id = request.POST.get('department_id')
            date = request.POST.get('date')
            shift_type = request.POST.get('shift_type')
            
            StaffShift.objects.create(
                doctor_id=doctor_id if doctor_id else None,
                staff_id=staff_id if staff_id else None,
                department_id=dept_id,
                date=date,
                shift_type=shift_type
            )
        return redirect('hospital-staffing')

class DischargeAndBillView(HospitalSetupMixin, View):
    """Generate consolidated hospital bill upon discharge."""
    def get(self, request, admission_id):
        admission = get_object_or_404(Admission, id=admission_id)
        
        # 1. Room Charges
        duration = (timezone.now() - admission.admission_date).days or 1
        room_charge = admission.bed.price_per_day * duration if admission.bed else 0
        
        # 2. Lab Charges
        lab_total = 0
        try:
            from apps.labs.models import LabOrder
            orders = LabOrder.objects.filter(patient=admission.patient)
            for order in orders:
                for test in order.tests.all():
                    lab_total += test.price
        except ImportError:
            pass

        # 3. Pharmacy Charges
        pharmacy_total = 0
        try:
            from apps.pharmacy.models import SaleItem, Medicine
            # Simplified: Pull all sale items associated with this patient
            # In a real system, we'd link prescriptions to admissions
            pass 
        except ImportError:
            pass

        grand_total = room_charge + lab_total + pharmacy_total
        
        context = {
            'hospital': self.get_hospital(),
            'admission': admission,
            'duration': duration,
            'room_charge': room_charge,
            'lab_total': lab_total,
            'pharmacy_total': pharmacy_total,
            'grand_total': grand_total,
        }
        return render(request, 'categories/hospital_invoice.html', context)

    def post(self, request, admission_id):
        admission = get_object_or_404(Admission, id=admission_id)
        # Discharge patient
        admission.status = 'DISCHARGED'
        admission.discharge_date = timezone.now()
        admission.save()
        
        # Free bed
        if admission.bed:
            admission.bed.status = 'AVAILABLE'
            admission.bed.save()
            
        return redirect('hospital-admissions')
