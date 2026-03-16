from django.db import migrations

def migrate_lab_items(apps, schema_editor):
    LabInventoryItem = apps.get_model('labs', 'LabInventoryItem')
    InventoryItem = apps.get_model('inventory', 'InventoryItem')
    InventoryBatch = apps.get_model('inventory', 'InventoryBatch')
    ItemType = apps.get_model('inventory', 'ItemType')
    
    # Pre-fetch types
    try:
        reagent_type = ItemType.objects.get(code='LAB_REAGENT')
        consumable_type = ItemType.objects.get(code='CONSUMABLE')
        equipment_type = ItemType.objects.get(code='EQUIPMENT')
        general_type = ItemType.objects.get(code='GENERAL')
    except Exception:
        # Silently skip if types are not seeded yet
        return

    type_map = {
        'REAGENT': reagent_type,
        'CONSUMABLE': consumable_type,
        'EQUIPMENT': equipment_type,
        'OTHER': general_type
    }

    for lab_item in LabInventoryItem.objects.all():
        item_type = type_map.get(lab_item.category, general_type)
        
        # Use SKU if available, otherwise generate one
        sku = lab_item.sku or f"LAB-{lab_item.id}"
        
        inv_item, created = InventoryItem.objects.get_or_create(
            sku=sku,
            defaults={
                'name': lab_item.name,
                'item_type': item_type,
                'unit': lab_item.unit,
                'min_stock_level': lab_item.reorder_level,
                'total_stock': lab_item.quantity_in_stock,
            }
        )
        
        if created and lab_item.quantity_in_stock > 0:
            InventoryBatch.objects.create(
                item=inv_item,
                batch_number=f"INIT-{sku}",
                quantity=lab_item.quantity_in_stock,
                expiry_date=lab_item.expiry_date
            )

def reverse_migrate(apps, schema_editor):
    pass

class Migration(migrations.Migration):

    dependencies = [
        ('labs', '0004_labinventoryitem_labinventorytransaction_and_more'),
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(migrate_lab_items, reverse_migrate),
    ]
