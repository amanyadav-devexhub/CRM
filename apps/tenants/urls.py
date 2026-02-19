from django.urls import path
from .views import TenantCreateAPIView

urlpatterns=[
    path('create-tenant/',TenantCreateAPIView.as_view(),name='create-tenant'),
]