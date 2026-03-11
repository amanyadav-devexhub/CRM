import uuid
from django.db import models
from django.conf import settings
from apps.core.models import AuditMixin, SoftDeleteMixin


# ──────────────────────────────────────────────
# 1. Patient Tag (for segmentation)
# ──────────────────────────────────────────────
class PatientTag(AuditMixin):
    """
    Reusable tags for patient segmentation.
    Examples: VIP, Chronic, Follow-up, Insurance, Walk-in
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)
    color = models.CharField(
        max_length=7, default="#3B82F6",
        help_text="Hex colour code for UI display"
    )
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "patient_tags"
        ordering = ["name"]

    def __str__(self):
        return self.name


# ──────────────────────────────────────────────
# 2. Patient (central entity)
# ──────────────────────────────────────────────
class Patient(AuditMixin, SoftDeleteMixin):
    """
    Core patient record. Uses UUID primary key and an auto-generated
    human-readable patient_id (e.g. PAT-00001).
    """

    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    class BloodGroup(models.TextChoices):
        A_POS = "A+", "A+"
        A_NEG = "A-", "A-"
        B_POS = "B+", "B+"
        B_NEG = "B-", "B-"
        AB_POS = "AB+", "AB+"
        AB_NEG = "AB-", "AB-"
        O_POS = "O+", "O+"
        O_NEG = "O-", "O-"

    class MaritalStatus(models.TextChoices):
        SINGLE = "single", "Single"
        MARRIED = "married", "Married"
        DIVORCED = "divorced", "Divorced"
        WIDOWED = "widowed", "Widowed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient_id = models.CharField(
        max_length=20, unique=True, editable=False,
        help_text="Auto-generated ID like PAT-00001"
    )

    # Demographics
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=Gender.choices, blank=True, default="")
    blood_group = models.CharField(max_length=3, choices=BloodGroup.choices, blank=True, default="")
    marital_status = models.CharField(max_length=20, choices=MaritalStatus.choices, blank=True, default="")

    # Contact
    email = models.EmailField(blank=True, default="")
    phone = models.CharField(max_length=20)
    secondary_phone = models.CharField(max_length=20, blank=True, default="")
    preferred_language = models.CharField(max_length=50, blank=True, default="English")

    # Profile
    profile_picture = models.ImageField(upload_to="patients/profile_pics/", blank=True, null=True)
    notes = models.TextField(blank=True, default="", help_text="Internal notes about the patient")

    # Segmentation
    tags = models.ManyToManyField(PatientTag, blank=True, related_name="patients")

    # Assigned Doctor
    assigned_doctor = models.ForeignKey(
        'clinical.Doctor',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="assigned_patients",
        help_text="Doctor primarily responsible for this patient"
    )

    # Linked user account (for patient portal login)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="patient_profile",
    )

    class Meta:
        db_table = "patients"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["phone"], name="idx_patient_phone"),
            models.Index(fields=["email"], name="idx_patient_email"),
            models.Index(fields=["last_name", "first_name"], name="idx_patient_name"),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.patient_id})"

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = self._generate_patient_id()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_patient_id():
        """Generate a sequential patient ID like PAT-00001."""
        last = Patient.all_objects.order_by("-patient_id").first()
        if last and last.patient_id.startswith("PAT-"):
            try:
                num = int(last.patient_id.split("-")[1]) + 1
            except (ValueError, IndexError):
                num = 1
        else:
            num = 1
        return f"PAT-{num:05d}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return (
            today.year - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )


# ──────────────────────────────────────────────
# 3. Address
# ──────────────────────────────────────────────
class Address(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="addresses")
    street = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default="India")
    is_primary = models.BooleanField(default=False)

    class Meta:
        db_table = "patient_addresses"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.street}, {self.city}"


# ──────────────────────────────────────────────
# 4. Emergency Contact
# ──────────────────────────────────────────────
class EmergencyContact(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="emergency_contacts")
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    relationship = models.CharField(max_length=50, help_text="e.g. Spouse, Parent, Sibling")

    class Meta:
        db_table = "patient_emergency_contacts"

    def __str__(self):
        return f"{self.name} ({self.relationship})"


# ──────────────────────────────────────────────
# 5. Medical History
# ──────────────────────────────────────────────
class MedicalHistory(AuditMixin):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        RESOLVED = "resolved", "Resolved"
        CHRONIC = "chronic", "Chronic"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="medical_history")
    condition = models.CharField(max_length=255)
    diagnosis_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True, default="")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)

    class Meta:
        db_table = "patient_medical_history"
        verbose_name_plural = "Medical histories"
        ordering = ["-diagnosis_date"]

    def __str__(self):
        return f"{self.condition} ({self.status})"


# ──────────────────────────────────────────────
# 6. Allergy
# ──────────────────────────────────────────────
class Allergy(AuditMixin):
    class Severity(models.TextChoices):
        MILD = "mild", "Mild"
        MODERATE = "moderate", "Moderate"
        SEVERE = "severe", "Severe"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="allergies")
    allergen = models.CharField(max_length=255)
    severity = models.CharField(max_length=10, choices=Severity.choices, default=Severity.MILD)
    reaction = models.TextField(blank=True, default="", help_text="Description of allergic reaction")

    class Meta:
        db_table = "patient_allergies"
        verbose_name_plural = "Allergies"

    def __str__(self):
        return f"{self.allergen} ({self.severity})"


# ──────────────────────────────────────────────
# 7. Insurance
# ──────────────────────────────────────────────
class Insurance(AuditMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="insurance_policies")
    provider = models.CharField(max_length=255)
    policy_number = models.CharField(max_length=100)
    group_number = models.CharField(max_length=100, blank=True, default="")
    valid_from = models.DateField()
    valid_to = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "patient_insurance"
        verbose_name_plural = "Insurance policies"

    def __str__(self):
        return f"{self.provider} – {self.policy_number}"

    @property
    def is_expired(self):
        from datetime import date
        return self.valid_to < date.today()


# ──────────────────────────────────────────────
# 8. Patient Document
# ──────────────────────────────────────────────
class PatientDocument(AuditMixin):
    class DocumentType(models.TextChoices):
        LAB_REPORT = "lab_report", "Lab Report"
        PRESCRIPTION = "prescription", "Prescription"
        SCAN = "scan", "Scan / X-Ray"
        CONSENT = "consent", "Consent Form"
        INSURANCE = "insurance", "Insurance Document"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="documents")
    file = models.FileField(upload_to="patients/documents/%Y/%m/")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices, default=DocumentType.OTHER)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
    )

    class Meta:
        db_table = "patient_documents"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.document_type})"


# ──────────────────────────────────────────────
# 9. Family Link
# ──────────────────────────────────────────────
class FamilyLink(AuditMixin):
    """Links two patients as family members / dependents."""

    class Relationship(models.TextChoices):
        SPOUSE = "spouse", "Spouse"
        PARENT = "parent", "Parent"
        CHILD = "child", "Child"
        SIBLING = "sibling", "Sibling"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="family_links")
    related_patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="related_to")
    relationship = models.CharField(max_length=10, choices=Relationship.choices)

    class Meta:
        db_table = "patient_family_links"
        unique_together = ["patient", "related_patient"]

    def __str__(self):
        return f"{self.patient} → {self.related_patient} ({self.relationship})"
