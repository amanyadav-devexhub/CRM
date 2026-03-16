from django.core.management.base import BaseCommand
from apps.accounts.models import Permission


class Command(BaseCommand):
    help = "Seed default system permissions"

    def handle(self, *args, **kwargs):

        permissions = [
            # Admin Dashboard
            ("dashboard.admin", "Admin Dashboard"),
            ("users.manage", "Manage Users"),
            ("roles.manage", "Manage Roles & Permissions"),
            ("departments.manage", "Manage Departments"),
            ("reports.view", "View Reports"),
            ("clinics.manage", "Manage Clinics"),
            ("audit.view", "View Audit Logs"),

            # Manager Dashboard
            ("dashboard.manager", "Manager Dashboard"),
            ("leave.manage", "Manage Leave Requests"),
            ("appointments.assign_doctor", "Assign Patients to Doctors"),
            ("staff.view_schedule", "View Staff Schedule"),
            ("appointments.moderate", "Moderate Appointments"),
            ("inventory.approve_requests", "Approve Inventory Requests"),

            # Doctor Dashboard
            ("dashboard.doctor", "Doctor Dashboard"),
            ("patients.view_records", "View Patient Records"),
            ("patients.edit_records", "Edit Patient Records"),
            ("patients.edit_medical_history", "Edit Medical History"),
            ("patients.edit_vitals", "Edit Vitals"),
            ("prescriptions.edit", "Edit Prescriptions"),
            ("prescriptions.issue", "Issue Prescriptions"),
            ("lab.view_results", "View Lab Results"),
            ("appointments.schedule", "Schedule Appointments"),

            # Nurse Dashboard
            ("dashboard.nurse", "Nurse Dashboard"),
            ("patients.update_vitals", "Update Patient Vitals"),
            ("procedures.assist", "Assist in Procedures"),
            ("appointments.manage_limited", "Manage Appointments (Limited)"),

            # Reception Dashboard
            ("dashboard.reception", "Reception Dashboard"),
            ("patients.register", "Patient Registration"),
            ("billing.access", "Billing Access (View/Process)"),
            ("notifications.send", "Send Notifications"),
            ("patients.check_in_out", "Check-in / Check-out Patients"),

            # Lab Dashboard
            ("dashboard.lab", "Lab Dashboard"),
            ("lab.upload_results", "Upload Lab Results"),
            ("lab.manage_inventory", "Manage Lab Inventory"),
            ("lab.schedule_tests", "Schedule Lab Tests"),

            # Pharmacy Dashboard
            ("dashboard.pharmacy", "Pharmacy Dashboard"),
            ("pharmacy.manage_inventory", "Manage Medicine Inventory"),
            ("pharmacy.dispense", "Dispense Prescriptions"),
            ("pharmacy.view_prescriptions", "View Patient Prescriptions"),
            ("pharmacy.update_stock", "Update Stock Levels"),

            # Patient Portal
            ("dashboard.patient", "Patient Portal"),
            ("patients.view_own_records", "View Own Records"),
            ("billing.pay", "Pay Bills"),
            ("notifications.receive", "Receive Notifications"),
        ]

        # To keep things clean, we will just add/update these. 
        # For a full reset, one might delete old ones, but to avoid FK issues we just ensure these exist.
        for code, name in permissions:
            Permission.objects.get_or_create(
                code=code,
                defaults={"name": name}
            )

        self.stdout.write(self.style.SUCCESS("Permissions seeded successfully"))
