from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from .models import InventoryItem, InventoryBatch, ItemType, ItemCategory, Supplier, StockTransaction
import uuid

class InventoryDashboardView(View):
    template_name = "inventory/inventory_dashboard.html"

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
            "item_types": ItemType.objects.filter(is_active=True),
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
        return redirect('inventory-dashboard')

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
                return redirect('inventory-dashboard')
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
        return redirect('inventory-dashboard')

class GetCategoriesView(View):
    """AJAX view to get categories for a selected type."""
    def get(self, request):
        type_id = request.GET.get('type_id')
        from django.http import JsonResponse
        categories = ItemCategory.objects.filter(item_type_id=type_id, is_active=True).values('id', 'name')
        return JsonResponse(list(categories), safe=False)
