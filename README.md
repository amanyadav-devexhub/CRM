# HealthCRM (SaaS Multi-Tenant Healthcare CRM)

HealthCRM is a comprehensive, highly-scalable, multi-tenant Customer Relationship Management (CRM) system designed from the ground up for modern healthcare providers. It provides a full suite of tools to gracefully manage hospitals, clinics, and pharmacies across totally isolated database schemas while maintaining a beautiful, responsive user interface.

## Core Architecture

HealthCRM is built on a robust set of technologies targeted towards security, performance, and strict data isolation.

- **Backend Framework**: Django (Python 3.8+)
- **Database Architecture**: PostgreSQL leveraging `django-tenants` for strict schema-based multi-tenancy (each clinic gets its own isolated schema).
- **Frontend Presentation**: Django Templates, HTML5, Vanilla CSS3 (utilizing modern UI systems, vivid gradients, and glassmorphism without heavy external frameworks).
- **Authentication**: Dual-layer with JWT-based API endpoints and secure session-based web authentication via OTP verification.

## Platform Features & Modules

### Multi-Tenancy Engine (SaaS Layer)
- **Data Isolation**: Each tenant (clinic, hospital, pharmacy) operates in a completely isolated environment to ensure HIPAA compliance and data security.
- **SuperAdmin Dashboard**: A "Public Schema" dedicated natively to platform administrators to monitor health metrics, manage Subscriptions, and oversee Platform Configurations.
- **Feature Flags**: SuperAdmins can dynamically toggle major application modules (e.g., Pharmacy, Labs, AI Analytics) on or off for specific tenants or entire industry categories.
- **Global Broadcast System**: SuperAdmins can push targeted, real-time ticker-tape announcements (e.g., "Scheduled Maintenance", "New Update") to specific tenants or all organizations simultaneously.

### Role-Based Access Control (RBAC)
- **Dynamic Role Creation**: Tenant administrators can define sophisticated custom roles with deeply granular permissions for Doctors, Receptionists, Lab Techs, and Pharmacists.
- **Template Synchronization**: SuperAdmins globally control "Category Role Templates" that trickle-down and synchronize with individual tenant roles.
- **Intelligent Permission Guards**: Navigation links, dashboard widgets, and action buttons dynamically render (or hide) strictly based on the logged-in user's evaluated permission flags.

### Patient & Clinical Management
- **Electronic Health Records (EHR)**: Centralized records for complex patient demographics and visit iterations.
- **Medical History & Document CRUD**: Real-time modal forms for logging allergies, past surgeries, and chronic conditions. Includes an integrated secure file upload system for scans and blood reports.
- **Appointments**: Interactive calendar systems for scheduling tracking.

### Pharmacy & Laboratory Integrations
- **Live Inventory**: Track medicine stock across distinct pharmacy subdivisions.
- **Point of Sale (POS)**: Intelligently fetch prescribed medicines and lab tests directly onto a patient's bill, actively decrementing inventory batches limits in real-time.
- **Specialized Lab Orders**: Seamlessly manage sample collection workflows, test execution, and PDF report delivery straight to patient profiles.

### Business & Analytics
- **Role-Specific Dashboards**: Contextual overviews crafted distinctively for doctors (clinical actions), receptionists (traffic), and administrators (revenue tracking).
- **Billing & Invoicing**: Comprehensive invoice staging, multi-line billing, and secure financial auditing.

## Project Structure

The codebase is structured under an organized, modular Django app paradigm:

- `accounts/` - User models, dual-authentication, tenant registration, OTP logic.
- `ai/` - AI-augmented clinical predictions and metric analysis.
- `analytics/` - High-level tenant aggregations and dashboards.
- `appointments/` - Calendar and scheduling logic.
- `billing/` - Invoice generation and revenue management.
- `clinical/` - Point-of-care patient charting and diagnosis logging.
- `communications/` - Messaging logic and SMS/Email bridging interfaces.
- `core/` - Abstract base classes, global models, common mixins.
- `labs/` - Laboratory test catalogs, sample collection tracking, results logging.
- `notifications/` - Internal alert channels and broadcast reception.
- `patients/` - Patient profile CRUD, Medical history, explicit document uploads.
- `pharmacy/` - POS configurations, medicine inventory levels, supplier routing.
- `tenants/` - The core engine for Schema-routing, Tenant initialization, and globally scoped Feature flags.
- `utils/` - Shared helper mechanics and utilities.

## Prerequisites

- Python 3.8+
- PostgreSQL or SQLite (depending on your configuration)

## Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd CRM
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply migrations**
   ```bash
   python manage.py migrate
   ```

5. **(Optional) Generate Dummy Data**
   If you want to populate the database with sample data:
   ```bash
   python generate_dummy_data.py
   python manage.py seed_plans
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

7. **Access the application**
   Open your browser and navigate to `http://127.0.0.1:8000/`.

## License

This project is licensed under the MIT License.
