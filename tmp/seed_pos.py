from django_tenants.utils import schema_context
from apps.inventory.models import InventoryItem, InventoryBatch, ItemType, Supplier
from decimal import Decimal
import uuid

def seed_pos_data():
    with schema_context('enterprise-clinic'):
        # 1. Get or create Medicine type
        med_type, _ = ItemType.objects.get_or_create(code='MEDICINE', defaults={'name': 'Medicine'})
        
        # 2. Get or create a Supplier
        supplier, _ = Supplier.objects.get_or_create(name='PharmaCorp Limited', defaults={'email': 'contact@pharmacorp.com'})
        
        # 3. Create some medicines
        medicines = [
            ('Paracetamol 500mg', 'PARA-500', 25.0, 5.0),
            ('Amoxicillin 250mg', 'AMOX-250', 120.0, 12.0),
            ('Ibuprofen 400mg', 'IBU-400', 45.0, 5.0),
            ('Cetirizine 10mg', 'CET-10', 15.0, 5.0),
            ('Omeprazole 20mg', 'OME-20', 180.0, 12.0),
        ]
        
        for name, sku, price, tax in medicines:
            item, created = InventoryItem.objects.get_or_create(
                sku=sku,
                defaults={
                    'name': name,
                    'item_type': med_type,
                    'unit': 'strips',
                    'supplier': supplier,
                }
            )
            
            # Add stock via a batch if none exists
            if not item.batches.exists():
                InventoryBatch.objects.create(
                    item=item,
                    batch_number=f"BATCH-{uuid.uuid4().hex[:6].upper()}",
                    quantity=Decimal('100.00'),
                    purchase_price=Decimal(price * 0.7),
                    selling_price=Decimal(price),
                    mrp=Decimal(price * 1.1),
                    tax_rate=Decimal(tax)
                )
            
            # Update total_stock
            item.update_stock_status()
            print(f"Created/Updated {name}: Stock={item.total_stock}")

if __name__ == "__main__":
    seed_pos_data()
