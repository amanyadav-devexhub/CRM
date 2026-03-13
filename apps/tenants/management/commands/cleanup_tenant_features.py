"""
cleanup_tenant_features — Remove stale TenantFeature records that were
auto-provisioned during onboarding. After this, features will be derived
from the subscription plan directly.

Usage:  python manage.py cleanup_tenant_features
"""
from django.core.management.base import BaseCommand
from apps.tenants.models import TenantFeature


class Command(BaseCommand):
    help = "Remove all TenantFeature records (stale overrides from onboarding)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting.",
        )

    def handle(self, *args, **options):
        qs = TenantFeature.objects.all()
        count = qs.count()

        if options["dry_run"]:
            self.stdout.write(f"Would delete {count} TenantFeature record(s).")
            for tf in qs[:20]:
                self.stdout.write(f"  - {tf.tenant.name}: {tf.feature_name} (enabled={tf.is_enabled})")
            if count > 20:
                self.stdout.write(f"  ... and {count - 20} more")
        else:
            qs.delete()
            self.stdout.write(self.style.SUCCESS(f"✅ Deleted {count} TenantFeature record(s)."))
            self.stdout.write("Features will now be derived from subscription plans.")
