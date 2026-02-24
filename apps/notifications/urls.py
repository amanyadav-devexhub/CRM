from django.urls import path
from .views import (
    NotificationListAPIView,
    NotificationMarkReadAPIView,
    NotificationMarkAllReadAPIView,
    NotificationPreferenceAPIView,
)

urlpatterns = [
    # Notifications
    path("", NotificationListAPIView.as_view(), name="notification-list"),
    path("<uuid:pk>/read/", NotificationMarkReadAPIView.as_view(), name="notification-mark-read"),
    path("mark-all-read/", NotificationMarkAllReadAPIView.as_view(), name="notification-mark-all-read"),

    # Preferences
    path("preferences/", NotificationPreferenceAPIView.as_view(), name="notification-preferences"),
]
