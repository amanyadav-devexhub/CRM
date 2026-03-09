"""
Data migration: seed default healthcare categories and backfill Tenant.category_obj.
"""
from django.db import migrations


DEFAULT_CATEGORIES = [
    {
        "code": "CLINIC",
        "name": "Clinic",
        "description": "Small to mid practice",
        "icon": "local_hospital",
        "color": "green",
        "sort_order": 1,
    },
    {
        "code": "HOSPITAL",
        "name": "Hospital",
        "description": "Multi-department facility",
        "icon": "apartment",
        "color": "blue",
        "sort_order": 2,
    },
    {
        "code": "LAB",
        "name": "Laboratory",
        "description": "Diagnostics & testing",
        "icon": "biotech",
        "color": "purple",
        "sort_order": 3,
    },
    {
        "code": "PHARMACY",
        "name": "Pharmacy",
        "description": "Retail / chain pharmacy",
        "icon": "medication",
        "color": "orange",
        "sort_order": 4,
    },
]


def seed_categories_and_backfill(apps, schema_editor):
    Category = apps.get_model("tenants", "Category")
    Tenant = apps.get_model("tenants", "Tenant")

    # 1. Seed default categories (skip if code already exists)
    for cat_data in DEFAULT_CATEGORIES:
        Category.objects.get_or_create(
            code=cat_data["code"],
            defaults=cat_data,
        )

    # 2. Backfill category_obj on existing tenants
    cat_map = {c.code: c for c in Category.objects.all()}
    updated = 0
    for tenant in Tenant.objects.filter(category_obj__isnull=True):
        cat = cat_map.get(tenant.category)
        if cat:
            tenant.category_obj = cat
            tenant.save(update_fields=["category_obj"])
            updated += 1

    print(f"  ↳ Seeded {len(DEFAULT_CATEGORIES)} default categories, backfilled {updated} tenant(s).")


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_categories_and_backfill, reverse_noop),
    ]
