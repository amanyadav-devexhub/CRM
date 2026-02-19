# Multi-Tenant Healthcare CRM — Implementation Plan

> **Project**: Cloud-based, subscription-driven Healthcare CRM  
> **Stack**: Django 5.x · django-tenants · Django REST Framework · Celery · PostgreSQL  
> **Date**: February 19, 2026

---

## 1. Project Overview

The Multi-Tenant Healthcare CRM is a SaaS platform designed to centralize operations for clinics, hospitals, and healthcare chains. It manages **patients, appointments, billing, labs, pharmacy, communications, staff, and AI-powered insights** — all behind a multi-tenant architecture with tiered subscription pricing.

### Target Users

| Tier | Users | Scale |
|------|-------|-------|
| **Basic** | Small clinics | 1–5 doctors |
| **Pro** | Medium hospitals / multi-specialty clinics | 5–50 doctors |
| **Enterprise** | Large hospitals & chains | 50+ doctors, multi-branch |

### Key Differentiators

- Multi-tenant data isolation with `django-tenants` (schema-per-tenant)
- Modular feature toggling per subscription plan
- 12 AI-powered features (appointment assistant, triage, clinical notes, no-show prediction, etc.)
- Communication-first (WhatsApp, SMS, email integration)
- HIPAA / GDPR compliance built-in

---

## 2. Current Codebase Status

### ✅ Completed

| Component | Status | Details |
|-----------|--------|---------|
| Project scaffolding | Done | Django project with `config/` settings, `apps/` directory |
| Settings architecture | Done | `base.py`, `development.py`, split SHARED_APPS / TENANT_APPS |
| `django-tenants` integration | Done | `Client` (TenantMixin), `Domain` (DomainMixin) models, PostgreSQL backend |
| Tenants app | Partially done | `Tenant`, `SubscriptionPlan`, `TenantSubscription` models, views, serializers, services, middleware |
| All 13 apps scaffolded | Done | `core`, `accounts`, `tenants`, `patients`, `appointments`, `billing`, `clinical`, `communications`, `labs`, `pharmacy`, `analytics`, `ai`, `notifications` |
| Requirements | Done | Django 5.x, django-tenants, DRF, celery, corsheaders, psycopg2-binary |
| URL routing | Partial | Only `admin/` and `api/tenants/` configured |

### ❌ Not Yet Implemented

- All apps except `tenants` have **empty** models, views, forms, and URLs
- No templates created
- No static files / frontend
- No Celery tasks configured
- No AI services implemented
- No test coverage
- Custom `User` model referenced (`accounts.User`) but not yet created

---

## 3. Implementation Phases

The project should be built in **7 phases**, ordered by dependency. Each phase builds on the previous.

---

### Phase 1 — Core & Tenant Foundation *(HIGH PRIORITY)*

> Establish the multi-tenant backbone, custom user model, and role-based access.

#### 1.1 Core App (`apps/core/`)

| Task | Description |
|------|-------------|
| `TenantAwareMixin` | Abstract model mixin that auto-sets `tenant` FK on save |
| `AuditMixin` | Adds `created_by`, `updated_by`, `created_at`, `updated_at` to models |
| `SoftDeleteMixin` | Adds `is_deleted`, `deleted_at` with queryset manager override |
| `TenantMiddleware` | Middleware to resolve tenant from subdomain/header and set `request.tenant` |
| `SecurityHeadersMiddleware` | Adds HIPAA/GDPR security headers to all responses |
| `encryption.py` | Utilities for encrypting sensitive patient data at rest |
| `tenant_context.py` | Thread-local utility to get/set current tenant |
| `core_tags.py` | Template tags for tenant-aware rendering |

#### 1.2 Accounts App (`apps/accounts/`)

| Task | Description |
|------|-------------|
| `User` model | Custom user extending `AbstractBaseUser` + `PermissionsMixin`; fields: email (login), first/last name, phone, tenant FK, role FK, is_active |
| `Role` model | Roles: SuperAdmin, TenantAdmin, Doctor, Nurse, Receptionist, LabTech, Pharmacist, Patient |
| `Permission` model | Granular permissions mapped to roles |
| `UserSession` model | Track active sessions, device info, IP |
| `TenantAuthenticationBackend` | Custom auth backend scoping login to tenant |
| Auth views | Login, logout, register, password reset, profile |
| Auth templates | `login.html`, `register.html`, `password_reset.html`, `profile.html` |
| Signals | Auto-create profile on user creation |

#### 1.3 Tenants App — Enhancements (`apps/tenants/`)

| Task | Description |
|------|-------------|
| `TenantConfiguration` model | Per-tenant settings (logo, theme, timezone, currency, language) |
| `TenantFeature` model | Feature toggles per tenant (e.g., `pharmacy_enabled`, `ai_enabled`) |
| Tenant onboarding API | Complete registration flow: create schema → seed defaults → assign plan |
| Subscription management | Plan upgrade/downgrade, billing cycle, trial expiry logic |
| Admin views | SuperAdmin dashboard to manage all tenants |

**Dependencies**: None (foundational)

---

### Phase 2 — Patient Management *(HIGH PRIORITY)*

> Build the patient registry — the central entity in the CRM.

#### 2.1 Patients App (`apps/patients/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `Patient` | UUID PK, first_name, last_name, dob, gender, email, phone, blood_group, tenant FK |
| `Address` | Patient FK, street, city, state, zip, country, is_primary |
| `EmergencyContact` | Patient FK, name, phone, relationship |
| `MedicalHistory` | Patient FK, condition, diagnosis_date, notes, status (active/resolved) |
| `Allergy` | Patient FK, allergen, severity, reaction |
| `Insurance` | Patient FK, provider, policy_number, group_number, valid_from, valid_to |

**Features:**
- Patient CRUD (API + templates)
- Patient search & filtering (name, phone, ID, tag)
- Patient tagging & segmentation (VIP, chronic, follow-up, insurance type)
- Family/dependent linking
- Document uploads (scans, reports, consent forms)
- Consent & compliance management
- Patient portal view (read-only records, download prescriptions)

**API Endpoints:**
```
GET    /api/patients/                    # List (paginated, filterable)
POST   /api/patients/                    # Create
GET    /api/patients/{id}/               # Detail
PUT    /api/patients/{id}/               # Update
DELETE /api/patients/{id}/               # Soft delete
GET    /api/patients/{id}/medical-history/
POST   /api/patients/{id}/medical-history/
GET    /api/patients/{id}/allergies/
GET    /api/patients/{id}/insurance/
GET    /api/patients/{id}/documents/
POST   /api/patients/{id}/documents/
```

**Templates:**
- `patients/list.html` — Patient list with search, filter, pagination
- `patients/detail.html` — Full patient profile view
- `patients/create.html` — Registration form
- `patients/medical_history.html` — History timeline view

**Dependencies**: Phase 1 (Core + Accounts)

---

### Phase 3 — Appointments & Scheduling *(HIGH PRIORITY)*

> Implement doctor calendars, slot management, queue system, and reminders.

#### 3.1 Appointments App (`apps/appointments/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `Schedule` | Doctor FK, day_of_week, start_time, end_time, slot_duration, is_active, branch |
| `TimeSlot` | Schedule FK, date, start_time, end_time, status (available/booked/blocked) |
| `Appointment` | UUID PK, patient FK, doctor FK, timeslot FK, type (consultation/follow-up/emergency), status (scheduled/completed/cancelled/no-show), notes |
| `Queue` | Appointment FK, token_number, check_in_time, status (waiting/in-progress/completed) |
| `Calendar` | Doctor FK, date, blocked_slots, notes |

**Features:**
- Doctor-wise & department-wise scheduling
- Automatic slot generation from schedules
- Online booking (API + web)
- Walk-in & token-based queue management
- Appointment reschedule & cancellation
- Multi-branch scheduling support
- SMS/WhatsApp/email reminders (via Celery tasks)

**Services:**
- `scheduling_service.py` — Slot generation, conflict detection
- `availability_service.py` — Real-time availability checks

**API Endpoints:**
```
GET    /api/appointments/                  # List
POST   /api/appointments/                  # Book
GET    /api/appointments/{id}/             # Detail
PUT    /api/appointments/{id}/             # Reschedule
PATCH  /api/appointments/{id}/cancel/      # Cancel
GET    /api/doctors/{id}/availability/     # Available slots
GET    /api/queue/                         # Live queue
POST   /api/queue/check-in/               # Walk-in check-in
```

**Dependencies**: Phase 1 + Phase 2

---

### Phase 4 — Billing & Payments *(MEDIUM PRIORITY)*

> Invoice generation, multi-gateway payments, insurance claims.

#### 4.1 Billing App (`apps/billing/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `Invoice` | UUID PK, patient FK, appointment FK (optional), total, discount, tax, net_amount, status (draft/sent/paid/cancelled), due_date |
| `InvoiceItem` | Invoice FK, description, quantity, unit_price, total |
| `Payment` | Invoice FK, amount, method (cash/card/UPI/wallet), gateway_ref, status, paid_at |
| `InsuranceClaim` | Invoice FK, insurance FK, claim_amount, status (submitted/approved/rejected/settled), pre_auth_number |
| `Tax` | Name (GST/VAT), rate, is_active |

**Integrations:**
- `stripe_integration.py` — Stripe payment gateway
- `razorpay_integration.py` — Razorpay payment gateway (India)
- `insurance_integration.py` — Insurance claim submission API

**Features:**
- Consultation billing & multi-service invoicing
- Partial & advance payments
- Refund & cancellation management
- Insurance claim support & pre-authorization tracking
- GST/tax compliance reports
- Receipt generation (PDF)

**Dependencies**: Phase 2 + Phase 3

---

### Phase 5 — Clinical, Labs & Pharmacy *(MEDIUM PRIORITY)*

> EMR capabilities, lab integration, pharmacy inventory.

#### 5.1 Clinical App (`apps/clinical/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `ClinicalNote` | Appointment FK, doctor FK, patient FK, note_type (SOAP/free-text), subjective, objective, assessment, plan |
| `Prescription` | ClinicalNote FK, patient FK, medicines (JSON), instructions, valid_until |
| `VitalSigns` | Patient FK, appointment FK, BP, pulse, temperature, weight, height, SpO2, recorded_at |
| `Diagnosis` | Patient FK, appointment FK, ICD_code, description, severity |
| `Procedure` | Patient FK, appointment FK, name, description, notes |

**Features:**
- SOAP note creation with templates
- Prescription management
- Vital signs recording
- Diagnosis with ICD coding
- Medical procedure documentation

#### 5.2 Labs App (`apps/labs/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `LabTest` | Name, code, category, reference_range, price |
| `LabOrder` | Patient FK, doctor FK, tests (M2M), status (ordered/collected/processing/completed), priority |
| `LabSample` | LabOrder FK, sample_type, collection_time, collected_by |
| `LabResult` | LabOrder FK, test FK, value, unit, is_abnormal, verified_by, verified_at |

**Features:**
- Lab test catalog management
- Sample collection tracking
- Result upload & patient notification
- External lab integration API
- Abnormal value flagging

#### 5.3 Pharmacy App (`apps/pharmacy/`) — *Optional Module*

**Models:**

| Model | Key Fields |
|-------|------------|
| `Medicine` | Name, generic_name, category, manufacturer, unit_price |
| `Inventory` | Medicine FK, batch_number, quantity, expiry_date, supplier |
| `Dispensing` | Prescription FK, medicine FK, quantity, dispensed_by, dispensed_at |
| `Supplier` | Name, contact, address |

**Features:**
- Medicine inventory tracking
- Prescription-to-pharmacy automation
- Stock alerts & expiry tracking
- Supplier management
- Billing integration

**Dependencies**: Phase 2 + Phase 3 + Phase 4

---

### Phase 6 — Communications & Notifications *(MEDIUM PRIORITY)*

> Multi-channel patient engagement.

#### 6.1 Communications App (`apps/communications/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `MessageTemplate` | Name, channel (WhatsApp/SMS/email), subject, body, variables |
| `Message` | Patient FK, template FK, channel, status (queued/sent/delivered/failed), sent_at |
| `Campaign` | Name, template FK, segment_filter, scheduled_at, status |
| `Feedback` | Patient FK, appointment FK, rating, comments, submitted_at |

**Features:**
- Two-way messaging (WhatsApp, SMS, email)
- Broadcast messages (health alerts, offers, campaigns)
- Patient feedback & rating system
- Push notifications via portal

#### 6.2 Notifications App (`apps/notifications/`)

**Models:**

| Model | Key Fields |
|-------|------------|
| `Notification` | User FK, type, title, body, is_read, action_url, created_at |

**Features:**
- Real-time in-app notifications (via WebSocket/SSE)
- Notification preferences per user
- Notification history & read tracking

**Celery Tasks:**
- `send_appointment_reminder` — 24h & 1h before appointment
- `send_follow_up_reminder` — Post-visit follow-up
- `send_payment_reminder` — Overdue invoices
- `send_campaign_messages` — Batch campaign delivery
- `send_lab_result_notification` — When results are ready

**Dependencies**: Phase 1 + Phase 2

---

### Phase 7 — AI Features & Analytics *(LOWER PRIORITY — Build Last)*

> AI-powered automation and reporting dashboards.

#### 7.1 AI App (`apps/ai/`)

**AI Features (12 total):**

| # | Feature | Description | Priority |
|---|---------|-------------|----------|
| 1 | AI Appointment Assistant | NLP-based booking via chat | Medium |
| 2 | Symptom Checker & Triage | Pre-consult symptom collection + urgency scoring | High |
| 3 | Clinical Notes Automation | Voice/text → structured SOAP notes | High |
| 4 | Prescription Assistance | Drug suggestion + interaction checking | Medium |
| 5 | No-Show Prediction | ML model to predict missed appointments | Medium |
| 6 | Smart Follow-Up Engine | Auto-identify patients needing follow-ups | Medium |
| 7 | Patient Churn Prediction | Identify at-risk patients for retention | Low |
| 8 | Lab Report Analysis | Highlight abnormal values + patient explanations | Medium |
| 9 | Revenue & Performance Analytics | Predictive revenue + doctor performance | Low |
| 10 | WhatsApp Chat Agent | 24/7 automated patient support | Medium |
| 11 | Patient Risk Scoring | Chronic/high-risk patient assessment (Enterprise) | Low |
| 12 | Voice-to-Text Documentation | Spoken consultations → medical records | Medium |

**Services:**
- `clinical_note_ai.py` — OpenAI/LLM integration for note generation
- `triage_service.py` — Symptom analysis and urgency classification
- `prediction_service.py` — No-show, churn, follow-up predictions (scikit-learn / custom ML)
- `voice_to_text.py` — Speech-to-text transcription (Whisper API)

**ML Model Directory Structure:**
```
apps/ai/ml_models/
├── symptom_checker/     # Triage classification model
├── note_generator/      # Clinical note templates + LLM prompts
└── no_show_predictor/   # Trained prediction model + feature pipeline
```

#### 7.2 Analytics App (`apps/analytics/`)

**Features:**
- Dashboard: revenue, appointments, doctor performance (daily/monthly/yearly)
- Department-wise & doctor-wise analytics
- Patient retention, follow-up, and no-show reports
- Custom report builder
- AI-powered insights (trends, risk predictions)

**Dependencies**: All previous phases

---

## 4. Database Architecture

### Multi-Tenancy Strategy

```
PostgreSQL Database: healthcare_crm
├── public schema          → Shared tables (Client, Domain, SubscriptionPlan, Users)
├── tenant_clinic_abc      → Tenant-specific tables (Patient, Appointment, Invoice, etc.)
├── tenant_hospital_xyz    → Tenant-specific tables (isolated data)
└── ...
```

### Key Database Categories (from txt6.txt)

1. **Core & Tenant Management** — Client, Domain, Tenant, SubscriptionPlan, TenantSubscription, TenantConfiguration, TenantFeature
2. **Patient Management** — Patient, Address, EmergencyContact, MedicalHistory, Allergy, Insurance
3. **Appointment & Scheduling** — Schedule, TimeSlot, Appointment, Queue, Calendar
4. **Billing & Payments** — Invoice, InvoiceItem, Payment, InsuranceClaim, Tax
5. **Clinical & EMR** — ClinicalNote, Prescription, VitalSigns, Diagnosis, Procedure
6. **Lab & Diagnostics** — LabTest, LabOrder, LabSample, LabResult
7. **Pharmacy & Inventory** — Medicine, Inventory, Dispensing, Supplier
8. **Communications** — MessageTemplate, Message, Campaign, Feedback
9. **AI & Analytics** — AILog, PredictionResult, DashboardWidget
10. **Audit & Compliance** — AuditLog, ConsentRecord, DataAccessLog

### Indexing Strategy

- Composite indexes on `(tenant_id, created_at)` for all tenant-scoped tables
- Index on `Patient.phone`, `Patient.email` for search
- Index on `Appointment.date`, `Appointment.doctor_id` for calendar queries
- Index on `Invoice.status`, `Invoice.due_date` for billing queries
- Full-text search index on `Patient.first_name`, `Patient.last_name`

### Performance Optimizations

- Connection pooling with `pgbouncer`
- Query optimization with `select_related` / `prefetch_related`
- Redis caching for frequently accessed data (doctor schedules, tenant configs)
- Celery for all async tasks (reminders, notifications, report generation)
- Pagination on all list endpoints

---

## 5. Security Model

| Layer | Implementation |
|-------|---------------|
| **Authentication** | Custom JWT + session auth, MFA support |
| **Authorization** | Role-based access control (RBAC) with granular permissions |
| **Data Isolation** | Schema-per-tenant via `django-tenants` |
| **Encryption** | AES-256 at rest for PII; TLS 1.3 in transit |
| **Audit** | Full audit logging for all data changes |
| **Compliance** | HIPAA, GDPR, local regulation support |
| **Session** | Secure cookies, session timeout, concurrent session limits |
| **API** | Rate limiting, CORS configuration, input validation |

---

## 6. Tech Stack Summary

| Category | Technology |
|----------|-----------|
| Backend Framework | Django 5.x |
| Multi-tenancy | django-tenants 3.7+ |
| REST API | Django REST Framework 3.15+ |
| Task Queue | Celery 5.4+ with Redis broker |
| Database | PostgreSQL 15+ |
| Caching | Redis |
| Search | PostgreSQL full-text search (or Elasticsearch for scale) |
| AI/ML | OpenAI API, scikit-learn, Whisper API |
| Messaging | Twilio (SMS), WhatsApp Business API, SendGrid (email) |
| Payments | Stripe, Razorpay |
| File Storage | AWS S3 / MinIO |
| Deployment | Docker + Docker Compose → AWS/GCP |
| CI/CD | GitHub Actions |

---

## 7. Competitive Landscape Context

The platform competes against:

- **Enterprise**: Salesforce Health Cloud, Microsoft Dynamics 365, Epic Systems, Oracle Healthcare
- **Clinic-focused**: Practo, MocDoc, Clinicea, CareCloud, Athenahealth
- **India/APAC**: Healthray, KareXpert, Docfyn, LeadSquared, Zoho CRM

**Our differentiators**: Multi-tenant SaaS model with tiered pricing, 12 integrated AI features, and a communication-first approach — combining the depth of enterprise solutions with the accessibility and pricing of clinic-focused tools.

---

## 8. Recommended Implementation Order

```
Phase 1: Core & Tenant Foundation     ██████████ ~3 weeks
Phase 2: Patient Management           ████████   ~2 weeks
Phase 3: Appointments & Scheduling    ████████   ~2 weeks
Phase 4: Billing & Payments           ████████   ~2 weeks
Phase 5: Clinical, Labs & Pharmacy    ██████████ ~3 weeks
Phase 6: Communications & Notifs      ██████     ~1.5 weeks
Phase 7: AI Features & Analytics      ████████████ ~4 weeks
─────────────────────────────────────────────────
Total estimated:                                  ~17.5 weeks
```

### Immediate Next Steps

1. **Complete the `accounts` app** — Custom `User` model (already referenced in settings as `accounts.User`), Role, Permission models
2. **Build core mixins** — `TenantAwareMixin`, `AuditMixin`, `SoftDeleteMixin`
3. **Implement `patients` app models & APIs** — Highest business value, central entity
4. **Set up Celery** — Required for all async features (reminders, notifications)
5. **Add URL routing** for each app as they are built

---

## 9. File-Level Source Reference

| File | Content |
|------|---------|
| `text_files/txt1.txt` | Project description, scope (10 modules), target users, goals |
| `text_files/txt2.txt` | Competitive landscape — 30+ competitors categorized |
| `text_files/txt3.txt` | Detailed feature list with subscription tiering per module |
| `text_files/txt4.txt` | 12 AI features with descriptions |
| `text_files/txt5.txt` | Full Django project structure — app-level file layouts, templates |
| `text_files/txt6.txt` | Database model categories & optimization areas |
