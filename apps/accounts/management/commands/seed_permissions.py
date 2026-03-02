from django.core.management.base import BaseCommand
from apps.accounts.models import Permission


class Command(BaseCommand):
    help = "Seed default system permissions"

    def handle(self, *args, **kwargs):

        permissions = [
            # Patient
            ("patient.view", "View Patients"),
            ("patient.create", "Create Patient"),
            ("patient.update", "Update Patient"),
            ("patient.delete", "Delete Patient"),

            # Appointment
            ("appointment.view", "View Appointments"),
            ("appointment.create", "Create Appointment"),
            ("appointment.update", "Update Appointment"),
            ("appointment.cancel", "Cancel Appointment"),

            # Billing
            ("billing.view", "View Billing"),
            ("billing.create", "Create Invoice"),
            ("billing.collect_payment", "Collect Payment"),

            # Dashboards
            ("dashboard.clinic", "Clinic Admin Dashboard"),
            ("dashboard.doctor", "Doctor Dashboard"),
            ("dashboard.reception", "Receptionist Dashboard"),
            ("dashboard.hr", "HR Dashboard"),
            ("dashboard.lab", "Lab Dashboard"),
            ("dashboard.pharmacy", "Pharmacy Dashboard"),
        ]

        for code, name in permissions:
            Permission.objects.get_or_create(
                code=code,
                defaults={"name": name}
            )

        self.stdout.write(self.style.SUCCESS("Permissions seeded successfully"))
