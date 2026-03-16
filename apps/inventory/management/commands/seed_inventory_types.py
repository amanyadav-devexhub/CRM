from django.core.management.base import BaseCommand
from apps.inventory.models import ItemType, ItemCategory


SEED_DATA = {
    'MEDICINE': {
        'name': 'Medicine',
        'icon': 'medication',
        'categories': [
            ('TABLETS', 'Tablets'),
            ('CAPSULES', 'Capsules'),
            ('SYRUPS', 'Syrups'),
            ('INJECTIONS', 'Injections'),
            ('DROPS', 'Drops'),
            ('OINTMENTS', 'Ointments'),
            ('CREAMS', 'Creams'),
            ('POWDERS', 'Powders'),
            ('INHALERS', 'Inhalers'),
            ('VACCINES_MED', 'Vaccines'),
            ('IV_FLUIDS', 'IV Fluids'),
            ('ANTIBIOTICS', 'Antibiotics'),
            ('PAINKILLERS', 'Painkillers'),
            ('ANTISEPTICS', 'Antiseptics'),
            ('HORMONES', 'Hormones'),
            ('SUPPLEMENTS', 'Supplements'),
        ]
    },
    'LAB_REAGENT': {
        'name': 'Lab Reagent',
        'icon': 'science',
        'categories': [
            ('BIOCHEM_REAGENT', 'Biochemistry Reagents'),
            ('HEMA_REAGENT', 'Hematology Reagents'),
            ('MICRO_REAGENT', 'Microbiology Reagents'),
            ('SERO_REAGENT', 'Serology Reagents'),
            ('IMMUNO_REAGENT', 'Immunology Reagents'),
            ('MOLEC_REAGENT', 'Molecular Reagents'),
            ('URINE_REAGENT', 'Urine Analysis Reagents'),
            ('BLOOD_REAGENT', 'Blood Testing Reagents'),
        ]
    },
    'LAB_TEST_KIT': {
        'name': 'Lab Test Kit',
        'icon': 'biotech',
        'categories': [
            ('RAPID_KIT', 'Rapid Test Kits'),
            ('PCR_KIT', 'PCR Kits'),
            ('ANTIGEN_KIT', 'Antigen Test Kits'),
            ('PREGNANCY_KIT', 'Pregnancy Kits'),
            ('DIABETES_KIT', 'Diabetes Test Kits'),
            ('COVID_KIT', 'COVID Test Kits'),
            ('HIV_KIT', 'HIV Test Kits'),
        ]
    },
    'CONSUMABLE': {
        'name': 'Medical Consumable',
        'icon': 'medical_services',
        'categories': [
            ('SYRINGES', 'Syringes'),
            ('NEEDLES', 'Needles'),
            ('GLOVES', 'Gloves'),
            ('MASKS', 'Masks'),
            ('COTTON', 'Cotton'),
            ('GAUZE', 'Gauze'),
            ('BANDAGES', 'Bandages'),
            ('SURGICAL_TAPE', 'Surgical Tape'),
            ('IV_SETS', 'IV Sets'),
            ('CATHETERS', 'Catheters'),
            ('SWABS', 'Swabs'),
        ]
    },
    'SUPPLY': {
        'name': 'Medical Supply',
        'icon': 'local_shipping',
        'categories': []
    },
    'SURGICAL': {
        'name': 'Surgical Item',
        'icon': 'healing',
        'categories': []
    },
    'EQUIPMENT': {
        'name': 'Medical Equipment',
        'icon': 'precision_manufacturing',
        'categories': []
    },
    'IMPLANT': {
        'name': 'Implant',
        'icon': 'settings_accessibility',
        'categories': []
    },
    'DIAGNOSTIC': {
        'name': 'Diagnostic Item',
        'icon': 'monitor_heart',
        'categories': []
    },
    'CHEMICAL': {
        'name': 'Chemical',
        'icon': 'science',
        'categories': []
    },
    'VACCINE': {
        'name': 'Vaccine',
        'icon': 'vaccines',
        'categories': []
    },
    'BLOOD': {
        'name': 'Blood Product',
        'icon': 'bloodtype',
        'categories': []
    },
    'GAS': {
        'name': 'Oxygen & Gas',
        'icon': 'air',
        'categories': []
    },
    'RADIOLOGY': {
        'name': 'Radiology Supply',
        'icon': 'radiology',
        'categories': []
    },
    'GENERAL': {
        'name': 'General Item',
        'icon': 'inventory_2',
        'categories': []
    },
}


class Command(BaseCommand):
    help = 'Seed predefined ItemTypes and ItemCategories for the Global Inventory System.'

    def handle(self, *args, **options):
        types_created = 0
        cats_created = 0

        for code, data in SEED_DATA.items():
            item_type, created = ItemType.objects.get_or_create(
                code=code,
                defaults={
                    'name': data['name'],
                    'icon': data['icon'],
                }
            )
            if created:
                types_created += 1
                self.stdout.write(f"  ✔ Created ItemType: {data['name']}")

            for cat_code, cat_name in data.get('categories', []):
                _, cat_created = ItemCategory.objects.get_or_create(
                    code=cat_code,
                    defaults={
                        'item_type': item_type,
                        'name': cat_name,
                    }
                )
                if cat_created:
                    cats_created += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {types_created} types and {cats_created} categories."
        ))
