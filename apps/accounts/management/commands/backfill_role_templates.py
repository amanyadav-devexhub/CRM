"""
backfill_role_templates — Link existing tenant roles to their CategoryRoleTemplate source.

Usage:  python manage.py backfill_role_templates
"""
from django.core.management.base import BaseCommand
from apps.accounts.models import Role
from apps.tenants.models import CategoryRoleTemplate


class Command(BaseCommand):
    help = "Backfill source_template on existing Role objects by matching name + category."

    def handle(self, *args, **options):
        roles = Role.objects.filter(source_template__isnull=True, is_system_role=True)
        total = roles.count()
        linked = 0

        for role in roles:
            if not role.tenant or not role.tenant.category:
                continue

            template = CategoryRoleTemplate.objects.filter(
                category=role.tenant.category,
                name=role.name
            ).first()

            if template:
                role.source_template = template
                role.save(update_fields=["source_template"])
                linked += 1
                self.stdout.write(f"  Linked: {role.name} ({role.tenant.name}) → {template}")

        self.stdout.write(self.style.SUCCESS(f"\n✅ Backfill complete: {linked}/{total} roles linked to templates."))
