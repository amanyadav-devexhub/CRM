from django.urls import path
from .views import (
    InventoryDashboardView, InventoryItemCreateView,
    StockTransactionView, GetCategoriesView, RecordConsumptionView,
    SupplierListView, GetItemDetailsView, InventoryItemUpdateView,
    GetSupplierDetailsView, SupplierUpdateView
)

app_name = 'inventory'

urlpatterns = [
    path('', InventoryDashboardView.as_view(), name='inventory-dashboard'),
    path('suppliers/', SupplierListView.as_view(), name='inventory-suppliers'),
    path('suppliers/<uuid:pk>/edit/', SupplierUpdateView.as_view(), name='supplier-update'),
    path('suppliers/<uuid:pk>/details/', GetSupplierDetailsView.as_view(), name='supplier-details'),
    path('add/', InventoryItemCreateView.as_view(), name='inventory-item-create'),
    path('<uuid:pk>/transaction/', StockTransactionView.as_view(), name='inventory-transaction'),
    path('<uuid:pk>/edit/', InventoryItemUpdateView.as_view(), name='inventory-item-update'),
    path('<uuid:pk>/details/', GetItemDetailsView.as_view(), name='inventory-item-details'),
    path('record-consumption/', RecordConsumptionView.as_view(), name='record-consumption'),
    path('ajax/categories/', GetCategoriesView.as_view(), name='inventory-get-categories'),
]
