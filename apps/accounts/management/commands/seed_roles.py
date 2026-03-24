from django.core.management.base import BaseCommand
from apps.accounts.models import Role, Permission
from apps.tenants.models import Tenant, CategoryRoleTemplate, Category

class Command(BaseCommand):
    help = "Seed CategoryRoleTemplates for admin panel and assign to all tenants"

    def handle(self, *args, **kwargs):
        categories = Category.objects.all()
        if not categories.exists():
            self.stdout.write(self.style.WARNING("No categories found. Please create categories in the admin dashboard before seeding." ))
            return

        # 1. Seed CategoryRoleTemplates (Admin Panel Roles)
        role_definitions = {
            "Admin / Super Admin": {
                "code": "admin",
                "is_active": True,
                "is_admin": True,
                "perms": [
                    "dashboard.admin", "users.manage", "roles.manage", "departments.manage",
                    "reports.view", "clinics.manage", "billing.access", "audit.view"
                ]
            },
            "Clinic Manager / Head of Department": {
                "code": "manager",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.manager", "reports.view", "leave.manage", 
                    "appointments.assign_doctor", "staff.view_schedule", 
                    "appointments.moderate", "inventory.approve_requests"
                ]
            },
            "Doctor / Specialist": {
                "code": "doctor",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.doctor", "patients.view_records", "patients.edit_records",
                    "patients.edit_medical_history", "prescriptions.edit",
                    "patients.edit_vitals", "prescriptions.issue", "lab.view_results",
                    "appointments.schedule"
                ]
            },
            "Nurse / Assistant": {
                "code": "nurse",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.nurse", "patients.view_records", "patients.update_vitals",
                    "procedures.assist", "lab.view_results", "appointments.manage_limited"
                ]
            },
            "Receptionist / Front Desk": {
                "code": "receptionist",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.reception", "patients.register", "appointments.schedule",
                    "billing.access", "notifications.send", "patients.check_in_out"
                ]
            },
            "Lab Technician / Diagnostic Staff": {
                "code": "lab_technician",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.lab", "lab.upload_results", "lab.manage_inventory",
                    "lab.schedule_tests"
                ]
            },
            "Pharmacist": {
                "code": "pharmacist",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.pharmacy", "pharmacy.manage_inventory", "pharmacy.dispense",
                    "pharmacy.view_prescriptions", "pharmacy.update_stock"
                ]
            },
            "Patient / Portal Access": {
                "code": "patient",
                "is_active": True,
                "is_admin": False,
                "perms": [
                    "dashboard.patient", "patients.view_own_records", "lab.view_results",
                    "pharmacy.view_prescriptions", "appointments.schedule", "billing.pay",
                    "notifications.receive"
                ]
            }
        }

        self.stdout.write("--- Seeding Admin Panel Roles (CategoryRoleTemplate) ---")
        for cat in categories:
            for role_name, data in role_definitions.items():
                template, created = CategoryRoleTemplate.objects.get_or_create(
                    category=cat,
                    name=role_name,
                    defaults={
                        "code": data["code"],
                        "is_active": data["is_active"],
                        "is_admin_role": data["is_admin"]
                    }
                )
                
                # Update existing templates with new fields if they were already created
                if not created:
                    template.code = data["code"]
                    template.is_active = data["is_active"]
                    template.is_admin_role = data["is_admin"]
                    template.save()

                perm_objs = []
                for perm_code in data["perms"]:
                    try:
                        p = Permission.objects.get(code=perm_code)
                        perm_objs.append(p)
                    except Permission.DoesNotExist:
                        pass
                
                template.permissions.set(perm_objs)

        self.stdout.write(self.style.SUCCESS("CategoryRoleTemplates seeded successfully.\n"))

        # 2. Assign these templates to Tenants
        self.stdout.write("--- Assigning Roles to Tenants ---")
        tenants = Tenant.objects.all()

        for tenant in tenants:
            if tenant.category:
                templates = CategoryRoleTemplate.objects.filter(category=tenant.category)
            else:
                templates = CategoryRoleTemplate.objects.filter(category__code="CLINIC")

            for template in templates:
                role, created = Role.objects.get_or_create(
                    tenant=tenant,
                    name=template.name,
                    defaults={"is_system_role": True}
                )

                # Assign permissions
                role.permissions.set(template.permissions.all())
                
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Created role '{role.name}' for {tenant.name}"))
                else:
                    self.stdout.write(f"Updated role '{role.name}' for {tenant.name}")

        self.stdout.write(self.style.SUCCESS("\nAll roles seeded and mapped successfully!"))
