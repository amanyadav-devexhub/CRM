# HealthCRM (Multi-Tenant Healthcare CRM)

HealthCRM is a comprehensive, multi-tenant Customer Relationship Management (CRM) system designed specifically for healthcare providers. It provides a full suite of tools to manage clinics, pharmacies, and patient records efficiently.

## Features

- **Multi-Tenancy**: Support for multiple clinics or organizations under a single deployment.
- **Patient Management**: Centralized records for patient demographics, medical history, and visits.
- **Appointments & Scheduling**: Integrated calendar and appointment booking system.
- **Clinical Notes**: Secure and structured note-taking for doctors and practitioners.
- **Pharmacy & Inventory**: Manage medicines, track inventory, and handle prescriptions.
- **Billing & Invoicing**: Streamlined billing, payments, and financial tracking.
- **Lab Management**: Record and track laboratory tests and results.
- **Analytics & Reporting**: Insights into clinic performance, patient flow, and financial health.
- **Communications**: Integrated notifications and messaging.
- **AI Analytics**: Advanced AI-driven insights for healthcare management.

## Project Structure

The project is built using the Django framework and follows a modular app-based architecture:

- `accounts/` - User authentication and role-based access control.
- `ai/` - AI features and integrations.
- `analytics/` - Dashboards and data reporting.
- `appointments/` - Appointment scheduling logic.
- `billing/` - Invoices, payments, and financial records.
- `clinical/` - Electronic Health Records (EHR) and clinical notes.
- `communications/` - Messaging and notifications.
- `core/` - Shared utilities and core models.
- `labs/` - Laboratory test management.
- `notifications/` - System and user alerts.
- `patients/` - Patient profiles and histories.
- `pharmacy/` - Medicine inventory and point of sale.
- `tenants/` - Multi-tenancy isolation and management.
- `utils/` - Helper functions and tools.

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
