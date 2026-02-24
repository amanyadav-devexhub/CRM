from django.db import models
from django.conf import settings
import uuid
from apps.patients.models import Patient

class Hospital(models.Model):
    """Enterprise-level Hospital details."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    license_number = models.CharField(max_length=100)
    tax_id = models.CharField(max_length=100, blank=True)
    accreditation_info = models.TextField(blank=True)
    logo = models.ImageField(upload_to='hospital_logos/', null=True, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    is_multi_branch = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Department(models.Model):
    """Medical departments within the hospital."""
    hospital = models.ForeignKey(Hospital, on_delete=models.CASCADE, related_name='departments', null=True)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    head_of_department = models.ForeignKey('clinical.Doctor', on_delete=models.SET_NULL, null=True, related_name='headed_departments')
    revenue_tracking = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Ward(models.Model):
    """Wards within a department (e.g., ICU, General Ward, Private)."""
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='wards')
    name = models.CharField(max_length=100)
    floor = models.CharField(max_length=50, blank=True)
    ward_type = models.CharField(max_length=50, default='GENERAL') # GENERAL, ICU, SEMI_PRIVATE, PRIVATE

    def __str__(self):
        return f"{self.name} ({self.department.name})"

class Bed(models.Model):
    """Individual beds within a ward."""
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('CLEANING', 'Cleaning'),
        ('MAINTENANCE', 'Maintenance'),
    ]
    BED_TYPE_CHOICES = [
        ('GENERAL', 'General Ward'),
        ('SEMI_PRIVATE', 'Semi-Private'),
        ('PRIVATE', 'Private Room'),
        ('ICU', 'ICU'),
        ('ER', 'Emergency Room'),
    ]

    ward = models.ForeignKey(Ward, on_delete=models.CASCADE, related_name='beds', null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='beds', null=True)
    bed_number = models.CharField(max_length=20, unique=True)
    bed_type = models.CharField(max_length=20, choices=BED_TYPE_CHOICES, default='GENERAL')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    price_per_day = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"Bed {self.bed_number} ({self.ward.name if self.ward else self.department.name if self.department else 'N/A'})"

class Admission(models.Model):
    """Inpatient (IPD) Admissions."""
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('DISCHARGED', 'Discharged'),
        ('CRITICAL', 'Critical'),
        ('TRANSFER_PENDING', 'Transfer Pending'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='admissions')
    bed = models.ForeignKey(Bed, on_delete=models.SET_NULL, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, null=True)
    admission_date = models.DateTimeField(auto_now_add=True)
    expected_discharge = models.DateTimeField(null=True, blank=True)
    discharge_date = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    attending_doctor = models.ForeignKey('clinical.Doctor', on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    discharge_summary = models.TextField(blank=True)

    def __str__(self):
        return f"IPD: {self.patient.full_name} ({self.status})"

class CorporateAccount(models.Model):
    """Corporate accounts and insurance providers."""
    name = models.CharField(max_length=255)
    contact_person = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    credit_limit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class InsuranceClaim(models.Model):
    """Tracking insurance pre-auth and claims."""
    STATUS_CHOICES = [
        ('PENDING', 'Pending Pre-Auth'),
        ('APPROVED', 'Pre-Auth Approved'),
        ('REJECTED', 'Pre-Auth Rejected'),
        ('CLAIMED', 'Claim Filed'),
        ('SETTLED', 'Settled'),
    ]
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='claims')
    corporate_account = models.ForeignKey(CorporateAccount, on_delete=models.CASCADE)
    policy_number = models.CharField(max_length=100)
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    remarks = models.TextField(blank=True)

    def __str__(self):
        return f"Claim: {self.admission.patient.full_name} - {self.corporate_account.name}"

class ERCase(models.Model):
    """Emergency Room cases and triage."""
    TRIAGE_LEVELS = [
        (1, 'Immediate (Resuscitation)'),
        (2, 'Emergency'),
        (3, 'Urgent'),
        (4, 'Semi-Urgent'),
        (5, 'Non-Urgent'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_name = models.CharField(max_length=255)  # Can be unknown 'John Doe'
    patient = models.ForeignKey(Patient, on_delete=models.SET_NULL, null=True, blank=True)
    triage_level = models.IntegerField(choices=TRIAGE_LEVELS, default=3)
    arrival_time = models.DateTimeField(auto_now_add=True)
    chief_complaint = models.TextField()
    vitals_on_arrival = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=50, default='TRIAGE_PENDING') # TRIAGE_PENDING, BEING_SEEN, ADMITTED, DISCHARGED
    attending_doctor = models.ForeignKey('clinical.Doctor', on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['triage_level', 'arrival_time']

    def __str__(self):
        return f"ER: {self.patient_name} (Level {self.triage_level})"

class PatientVital(models.Model):
    """Clinical vitals monitoring for admitted patients."""
    admission = models.ForeignKey(Admission, on_delete=models.CASCADE, related_name='vitals')
    recorded_at = models.DateTimeField(auto_now_add=True)
    temperature = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    pulse = models.IntegerField(null=True, blank=True)
    systolic_bp = models.IntegerField(null=True, blank=True)
    diastolic_bp = models.IntegerField(null=True, blank=True)
    spo2 = models.IntegerField(null=True, blank=True)
    respiration_rate = models.IntegerField(null=True, blank=True)
    recorded_by = models.ForeignKey('clinical.Doctor', on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Vitals for {self.admission.patient.full_name} at {self.recorded_at}"

class HospitalStaff(models.Model):
    """Non-doctor clinical and support staff."""
    ROLE_CHOICES = [
        ('NURSE', 'Nurse'),
        ('TECHNICIAN', 'Lab Technician'),
        ('PHARMACIST', 'Pharmacist'),
        ('ADMIN', 'Administrator'),
        ('SUPPORT', 'Support Staff'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, related_name='staff')
    phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} ({self.get_role_display()})"

class StaffShift(models.Model):
    """Duty roster for clinical staff."""
    SHIFT_TYPES = [
        ('MORNING', 'Morning (08:00 - 16:00)'),
        ('EVENING', 'Evening (16:00 - 00:00)'),
        ('NIGHT', 'Night (00:00 - 08:00)'),
    ]
    
    doctor = models.ForeignKey('clinical.Doctor', on_delete=models.CASCADE, related_name='shifts', null=True, blank=True)
    staff = models.ForeignKey(HospitalStaff, on_delete=models.CASCADE, related_name='shifts', null=True, blank=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE)
    date = models.DateField()
    shift_type = models.CharField(max_length=20, choices=SHIFT_TYPES)
    is_on_call = models.BooleanField(default=False)

    def __str__(self):
        person = self.doctor.name if self.doctor else (self.staff.name if self.staff else 'Unknown')
        return f"Shift: {person} - {self.date} ({self.shift_type})"
