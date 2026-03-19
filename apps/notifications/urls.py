# apps/notifications/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import NotificationViewSet, NotificationPreferenceViewSet

# Create a router and register our viewsets
router = DefaultRouter()
router.register(r'', NotificationViewSet, basename='notification')
router.register(r'preferences', NotificationPreferenceViewSet, basename='preference')

# The API URLs are determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
]