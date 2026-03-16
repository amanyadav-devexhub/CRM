from django.urls import path
from .views import (
    InventoryDashboardView, InventoryItemCreateView,
    StockTransactionView, GetCategoriesView
)

urlpatterns = [
    path('', InventoryDashboardView.as_view(), name='inventory-dashboard'),
    path('add/', InventoryItemCreateView.as_view(), name='inventory-item-create'),
    path('<uuid:pk>/transaction/', StockTransactionView.as_view(), name='inventory-transaction'),
    path('ajax/categories/', GetCategoriesView.as_view(), name='inventory-get-categories'),
]
