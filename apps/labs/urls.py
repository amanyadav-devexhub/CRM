from django.urls import path
from .template_views import (
    LabTestCatalogView, LabOrderListView, LabOrderEntryView, 
    LabOrderPrintSlipView, LabReportView, 
    LabSampleCollectionView, LabProcessingView,
    LabAnalyticsView
)
from apps.tenants.template_views import CategoryLabsView

urlpatterns = [
    path('', CategoryLabsView.as_view(), name='labs-hub'),
    path('catalog/', LabTestCatalogView.as_view(), name='lab-test-catalog'),
    path('orders/', LabOrderListView.as_view(), name='lab-order-list'),
    path('samples/', LabSampleCollectionView.as_view(), name='lab-sample-collection'),
    path('processing/', LabProcessingView.as_view(), name='lab-processing'),
    path('analytics/', LabAnalyticsView.as_view(), name='lab-analytics'),
    path('orders/<uuid:order_id>/', LabOrderEntryView.as_view(), name='lab-order-entry'),
    path('orders/<uuid:order_id>/print/', LabOrderPrintSlipView.as_view(), name='lab-order-print'),
    path('orders/<uuid:order_id>/report/', LabReportView.as_view(), name='lab-report'),
]
