# apps/labs/urls.py
from django.urls import path
from .template_views import LabTestCatalogView, LabOrderListView, LabOrderEntryView
from apps.tenants.template_views import CategoryLabsView

urlpatterns = [
    path('', CategoryLabsView.as_view(), name='labs-hub'),
    path('catalog/', LabTestCatalogView.as_view(), name='lab-test-catalog'),
    path('orders/', LabOrderListView.as_view(), name='lab-order-list'),
    path('orders/<uuid:order_id>/', LabOrderEntryView.as_view(), name='lab-order-entry'),
]
