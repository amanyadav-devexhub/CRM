from django.core.management.base import BaseCommand
from apps.accounts.models import Role
from apps.tenants.models import Tenant, CategoryRoleTemplate


class Command(BaseCommand):
    help = "Seed default roles for all tenants based on their category templates"

    def handle(self, *args, **kwargs):
        tenants = Tenant.objects.all()

        for tenant in tenants:
            # Check if tenant has a category object, otherwise fallback to CLINIC string
            category_obj = tenant.category_obj
            category_code = tenant.category
            
            if category_obj:
                templates = CategoryRoleTemplate.objects.filter(category=category_obj)
            else:
                templates = CategoryRoleTemplate.objects.filter(category__code=category_code)

            if not templates.exists():
                self.stdout.write(self.style.WARNING(f"No templates found for {category_code}, falling back to CLINIC templates for {tenant.name}"))
                templates = CategoryRoleTemplate.objects.filter(category__code="CLINIC")
                
                if not templates.exists():
                    self.stdout.write(self.style.ERROR("No CLINIC fallback templates found either! Run seed_role_templates first."))
                    continue

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

        self.stdout.write(self.style.SUCCESS("Roles seeded successfully"))
