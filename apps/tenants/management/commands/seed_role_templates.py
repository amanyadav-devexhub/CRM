from django.core.management.base import BaseCommand
from apps.accounts.models import Permission
from apps.tenants.models import Category, CategoryRoleTemplate


class Command(BaseCommand):
    help = "Seed CategoryRoleTemplates for all categories"

    def handle(self, *args, **kwargs):
        
        categories = Category.objects.all()
        if not categories.exists():
            self.stdout.write(self.style.WARNING("No categories found. Please create categories in the admin dashboard before seeding." ))
            return

        role_definitions = {
            "Admin / Super Admin": {
                "is_admin": True,
                "perms": [
                    "dashboard.admin", "users.manage", "roles.manage", "departments.manage",
                    "reports.view", "clinics.manage", "billing.access", "audit.view"
                ]
            },
            "Clinic Manager / Head of Department": {
                "is_admin": False,
                "perms": [
                    "dashboard.manager", "reports.view", "leave.manage", 
                    "appointments.assign_doctor", "staff.view_schedule", 
                    "appointments.moderate", "inventory.approve_requests"
                ]
            },
            "Doctor / Specialist": {
                "is_admin": False,
                "perms": [
                    "dashboard.doctor", "patients.view_records", "patients.edit_records",
                    "patients.edit_medical_history", "prescriptions.edit",
                    "patients.edit_vitals", "prescriptions.issue", "lab.view_results",
                    "appointments.schedule", "appointments.moderate"
                ]
            },
            "Nurse / Assistant": {
                "is_admin": False,
                "perms": [
                    "dashboard.nurse", "patients.view_records", "patients.update_vitals",
                    "procedures.assist", "lab.view_results", "appointments.manage_limited"
                ]
            },
            "Receptionist / Front Desk": {
                "is_admin": False,
                "perms": [
                    "dashboard.reception", "patients.register", "appointments.schedule",
                    "billing.access", "notifications.send", "patients.check_in_out"
                ]
            },
            "Lab Technician / Diagnostic Staff": {
                "is_admin": False,
                "perms": [
                    "dashboard.lab", "lab.upload_results", "lab.manage_inventory",
                    "lab.schedule_tests"
                ]
            },
            "Pharmacist": {
                "is_admin": False,
                "perms": [
                    "dashboard.pharmacy", "pharmacy.manage_inventory", "pharmacy.dispense",
                    "pharmacy.view_prescriptions", "pharmacy.update_stock"
                ]
            },
            "Patient / Portal Access": {
                "is_admin": False,
                "perms": [
                    "dashboard.patient", "patients.view_own_records", "lab.view_results",
                    "pharmacy.view_prescriptions", "appointments.schedule", "billing.pay",
                    "notifications.receive"
                ]
            }
        }

        for cat in categories:
            self.stdout.write(f"Seeding templates for category: {cat.name} ({cat.code})")

            for role_name, data in role_definitions.items():
                template, _ = CategoryRoleTemplate.objects.get_or_create(
                    category=cat,
                    name=role_name,
                    defaults={
                        "is_admin_role": data["is_admin"]
                    }
                )
                # Need to update is_admin_role just in case it already existed
                if template.is_admin_role != data["is_admin"]:
                    template.is_admin_role = data["is_admin"]
                    template.save()

                perm_objs = []
                for perm_code in data["perms"]:
                    try:
                        p = Permission.objects.get(code=perm_code)
                        perm_objs.append(p)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Permission {perm_code} not found!"))
                
                template.permissions.set(perm_objs)

        self.stdout.write(self.style.SUCCESS("CategoryRoleTemplates seeded successfully for all categories"))
