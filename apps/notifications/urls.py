# apps/notifications/urls.py

from django.urls import path
from apps.notifications import api_views

app_name = 'notifications'

urlpatterns = [
    # ═══════════════════════════════════════════════════════════════
    # NOTIFICATION API ENDPOINTS
    # ═══════════════════════════════════════════════════════════════
    
    # List notifications (with count)
    # GET /api/notifications/
    # GET /api/notifications/?is_read=false  (filter unread)
    # GET /api/notifications/?limit=5  (limit results)
    path('', api_views.NotificationListView.as_view(), name='notification-list'),
    
    # Mark single notification as read
    # POST /api/notifications/{uuid}/mark-read/
    path('<uuid:pk>/mark-read/', api_views.MarkAsReadView.as_view(), name='mark-read'),
    
    # Mark all notifications as read
    # POST /api/notifications/mark-all-read/
    path('mark-all-read/', api_views.MarkAllAsReadView.as_view(), name='mark-all-read'),
    
    # Get single notification detail
    # GET /api/notifications/{uuid}/
    path('<uuid:pk>/', api_views.NotificationDetailView.as_view(), name='notification-detail'),
]