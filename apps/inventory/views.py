from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from .models import InventoryItem, InventoryBatch, ItemType, ItemCategory, Supplier, StockTransaction
import uuid

class InventoryDashboardView(View):
    template_name = "inventory/inventory_dashboard.html"
    
    def post(self, request):
        return self.get(request)

    def get(self, request):
        items = InventoryItem.objects.all().select_related('item_type', 'item_category')
        
        # Summary stats
        total_items = items.count()
        low_stock_count = items.filter(status='LOW_STOCK').count()
        out_of_stock_count = items.filter(status='OUT_OF_STOCK').count()
        
        # Expiring soon (within 30 days) across all batches
        expiring_soon_count = InventoryBatch.objects.filter(
            is_active=True,
            expiry_date__gt=timezone.now().date(),
            expiry_date__lte=timezone.now().date() + timezone.timedelta(days=30)
        ).values('item').distinct().count()

        return render(request, self.template_name, {
            "items": items,
            "total_items": total_items,
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count,
            "expiring_soon_count": expiring_soon_count,
            "item_types": ItemType.objects.all(),
        })

class InventoryItemCreateView(View):
    def post(self, request):
        name = request.POST.get('name')
        sku = request.POST.get('sku')
        type_id = request.POST.get('item_type')
        category_id = request.POST.get('item_category')
        unit = request.POST.get('unit', 'pcs')
        min_stock = request.POST.get('min_stock_level', 10)
        
        item_type = get_object_or_404(ItemType, id=type_id)
        item_category = None
        if category_id:
            item_category = get_object_or_404(ItemCategory, id=category_id)

        item = InventoryItem.objects.create(
            name=name,
            sku=sku,
            item_type=item_type,
            item_category=item_category,
            unit=unit,
            min_stock_level=min_stock
        )
        
        # Handle initial batch if provided
        batch_number = request.POST.get('batch_number')
        if batch_number:
            quantity = request.POST.get('quantity', 0)
            purchase_price = request.POST.get('purchase_price', 0)
            selling_price = request.POST.get('selling_price', 0)
            expiry_date = request.POST.get('expiry_date') or None
            
            batch = InventoryBatch.objects.create(
                item=item,
                batch_number=batch_number,
                quantity=quantity,
                purchase_price=purchase_price,
                selling_price=selling_price,
                expiry_date=expiry_date
            )
            
            # Record transaction
            StockTransaction.objects.create(
                item=item,
                batch=batch,
                transaction_type='IN',
                quantity=quantity,
                performed_by=request.user,
                notes="Initial stock entry"
            )
            
            item.update_stock_status()

        messages.success(request, f"Item '{name}' added to inventory.")
        return redirect('inventory:inventory-dashboard')

class StockTransactionView(View):
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        trans_type = request.POST.get('transaction_type')
        quantity = float(request.POST.get('quantity', 0))
        batch_id = request.POST.get('batch_id')
        notes = request.POST.get('notes', '')

        batch = None
        if batch_id:
            batch = get_object_or_404(InventoryBatch, id=batch_id)
        else:
            # If no batch selected for OUT/ADJUST, we might need to Pick one or create a new one for IN
            if trans_type == 'IN':
                # Create a generic batch if none specified? Or force batch selection.
                # For now, let's assume UI provides batch or we create a dummy one.
                pass

        if trans_type == 'OUT':
            if batch and batch.quantity >= quantity:
                batch.quantity -= quantity
                batch.save()
            else:
                messages.error(request, "Insufficient stock in selected batch.")
                return redirect('inventory:inventory-dashboard')
        elif trans_type == 'IN':
            if batch:
                batch.quantity += quantity
                batch.save()
        
        StockTransaction.objects.create(
            item=item,
            batch=batch,
            transaction_type=trans_type,
            quantity=quantity,
            performed_by=request.user,
            notes=notes
        )
        
        item.update_stock_status()
        messages.success(request, f"Stock {trans_type} recorded for {item.name}.")
        return redirect('inventory:inventory-dashboard')

class GetCategoriesView(View):
    """AJAX view to get categories for a selected type."""
    def get(self, request):
        type_id = request.GET.get('type_id')
        from django.http import JsonResponse
        categories = ItemCategory.objects.filter(item_type_id=type_id, is_active=True).values('id', 'name')
        return JsonResponse(list(categories), safe=False)

class SupplierListView(View):
    """View to manage inventory suppliers."""
    template_name = "inventory/supplier_list.html"
    def get(self, request):
        suppliers = Supplier.objects.all().prefetch_related('item_types')
        item_types = ItemType.objects.filter(is_active=True)
        return render(request, self.template_name, {
            "suppliers": suppliers,
            "item_types": item_types
        })

    def post(self, request):
        name = request.POST.get('name')
        contact_person = request.POST.get('contact_person', '')
        email = request.POST.get('email', '')
        phone = request.POST.get('phone', '')
        address = request.POST.get('address', '')
        gst_number = request.POST.get('gst_number', '')

        if not name:
            messages.error(request, "Supplier name is required.")
            return redirect('inventory:inventory-suppliers')

        supplier = Supplier.objects.create(
            name=name,
            contact_person=contact_person,
            email=email,
            phone=phone,
            address=address,
            gst_number=gst_number
        )
        
        item_type_ids = request.POST.getlist('item_types')
        if item_type_ids:
            supplier.item_types.set(item_type_ids)

        messages.success(request, f"Supplier '{name}' created successfully.")
        redirect_url = request.POST.get('redirect_url', 'inventory:inventory-suppliers')
        return redirect(redirect_url)

class RecordConsumptionView(View):
    """Record usage of a consumable item during a patient encounter."""
    def post(self, request):
        item_id = request.POST.get('item_id')
        patient_id = request.POST.get('patient_id')
        appointment_id = request.POST.get('appointment_id') or None
        quantity = float(request.POST.get('quantity', 0))
        is_billable = request.POST.get('is_billable') == 'true'
        notes = request.POST.get('notes', '')
        redirect_url = request.POST.get('redirect_url', '/dashboard/')

        if not item_id or quantity <= 0:
            messages.error(request, "Invalid item or quantity.")
            return redirect(redirect_url)

        item = get_object_or_404(InventoryItem, pk=item_id)
        
        if item.total_stock < quantity:
            messages.error(request, f"Insufficient stock for {item.name}. Available: {item.total_stock}")
            return redirect(redirect_url)

        # 1. Deduct stock (FIFO: First-In, First-Out by expiry/creation)
        remaining_to_deduct = quantity
        batches = item.batches.filter(is_active=True, quantity__gt=0).order_by('expiry_date', 'created_at')
        
        performed_transactions = []
        for batch in batches:
            if remaining_to_deduct <= 0:
                break
            
            deduct = min(float(batch.quantity), remaining_to_deduct)
            batch.quantity = float(batch.quantity) - deduct
            batch.save()
            
            tx = StockTransaction.objects.create(
                item=item,
                batch=batch,
                transaction_type='OUT',
                quantity=deduct,
                performed_by=request.user,
                patient_id=patient_id,
                appointment_id=appointment_id,
                is_billable=is_billable,
                notes=notes
            )
            performed_transactions.append(tx)
            remaining_to_deduct -= deduct
            
        item.update_stock_status()

        # 2. Billing Integration
        if is_billable and performed_transactions:
            from apps.billing.models import Invoice, InvoiceItem
            from django.db.models import Sum
            
            # Find or create a DRAFT invoice for the patient
            invoice = Invoice.objects.filter(patient_id=patient_id, status='DRAFT').first()
            if not invoice:
                invoice = Invoice.objects.create(
                    patient_id=patient_id,
                    status='DRAFT',
                    created_by=request.user,
                    notes=f"Auto-generated for consumables/supplies"
                )
            
            # Use price from the first batch used (common pattern)
            price = performed_transactions[0].batch.selling_price if performed_transactions[0].batch else 0
            
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f"Consumable: {item.name}",
                quantity=quantity,
                unit_price=price,
            )
            
            # Recalculate invoice totals
            subtotal = invoice.items.aggregate(total=Sum('total'))['total'] or 0
            invoice.subtotal = subtotal
            invoice.grand_total = subtotal # Assuming no tax/discount for auto-added items for now
            invoice.save()

        messages.success(request, f"Recorded use of {quantity} {item.unit} of {item.name}.")
        return redirect(redirect_url)

class GetItemDetailsView(View):
    """AJAX view to fetch item details for editing."""
    def get(self, request, pk):
        from django.http import JsonResponse
        item = get_object_or_404(InventoryItem, pk=pk)
        data = {
            'id': str(item.id),
            'name': item.name,
            'sku': item.sku,
            'item_type_id': str(item.item_type_id),
            'item_category_id': str(item.item_category_id) if item.item_category_id else '',
            'unit': item.unit,
            'min_stock_level': item.min_stock_level,
        }
        return JsonResponse(data)

class InventoryItemUpdateView(View):
    """View to handle inventory item updates."""
    def post(self, request, pk):
        item = get_object_or_404(InventoryItem, pk=pk)
        
        item.name = request.POST.get('name')
        item.sku = request.POST.get('sku')
        item.unit = request.POST.get('unit')
        item.min_stock_level = request.POST.get('min_stock_level', 10)
        
        type_id = request.POST.get('item_type')
        category_id = request.POST.get('item_category')
        
        if type_id:
            item.item_type = get_object_or_404(ItemType, id=type_id)
        if category_id:
            item.item_category = ItemCategory.objects.filter(id=category_id).first()
        else:
            item.item_category = None
            
        item.save()
        messages.success(request, f"Item '{item.name}' updated successfully.")
        return redirect('inventory:inventory-dashboard')

class GetSupplierDetailsView(View):
    """AJAX view to fetch supplier details for editing."""
    def get(self, request, pk):
        from django.http import JsonResponse
        supplier = get_object_or_404(Supplier, pk=pk)
        data = {
            'id': str(supplier.id),
            'name': supplier.name,
            'contact_person': supplier.contact_person,
            'email': supplier.email,
            'phone': supplier.phone,
            'address': supplier.address,
            'gst_number': supplier.gst_number,
            'is_active': supplier.is_active,
            'item_types': [str(tid) for tid in supplier.item_types.values_list('id', flat=True)],
        }
        return JsonResponse(data)

class SupplierUpdateView(View):
    """View to handle supplier updates."""
    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        
        supplier.name = request.POST.get('name')
        supplier.contact_person = request.POST.get('contact_person')
        supplier.email = request.POST.get('email')
        supplier.phone = request.POST.get('phone')
        supplier.address = request.POST.get('address')
        supplier.gst_number = request.POST.get('gst_number')
        
        # is_active logic (checkbox)
        supplier.is_active = 'is_active' in request.POST
        
        # item_types logic
        item_type_ids = request.POST.getlist('item_types')
        supplier.item_types.set(item_type_ids)
        
        supplier.save()
        messages.success(request, f"Supplier '{supplier.name}' updated successfully.")
        return redirect('inventory:inventory-suppliers')
