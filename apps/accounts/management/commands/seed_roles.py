from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Seed default roles for all tenants"

    def handle(self, *args, **kwargs):

        tenants = Tenant.objects.all()

        for tenant in tenants:

            admin_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Admin",
                defaults={"is_system_role": True}
            )

            doctor_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Doctor",
                defaults={"is_system_role": True}
            )

            receptionist_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Receptionist",
                defaults={"is_system_role": True}
            )

            billing_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name="Billing Staff",
                defaults={"is_system_role": True}
            )

            # Assign Permissions
            self.assign_permissions(admin_role, all_permissions=True)
            self.assign_permissions(doctor_role, doctor=True)
            self.assign_permissions(receptionist_role, receptionist=True)
            self.assign_permissions(billing_role, billing=True)

        self.stdout.write(self.style.SUCCESS("Roles seeded successfully"))

    def assign_permissions(self, role, all_permissions=False, doctor=False, receptionist=False, billing=False):

        if all_permissions:
            role.permissions.set(Permission.objects.all())
            return

        if doctor:
            perms = Permission.objects.filter(code__startswith="patient.") | \
                    Permission.objects.filter(code__startswith="appointment.")
            role.permissions.set(perms)

        if receptionist:
            perms = Permission.objects.filter(code__in=[
                "patient.view",
                "patient.create",
                "appointment.view",
                "appointment.create",
            ])
            role.permissions.set(perms)

        if billing:
            perms = Permission.objects.filter(code__startswith="billing.")
            role.permissions.set(perms)
