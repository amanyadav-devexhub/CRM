from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404

from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer


# ══════════════════════════════════════════════
# Notifications
# ══════════════════════════════════════════════

class NotificationListAPIView(APIView):
    """
    GET  /api/notifications/     → list notifications for the current user
    POST /api/notifications/     → create a notification (system use)
    """

    def get(self, request):
        if request.user.is_authenticated:
            notifications = Notification.objects.filter(user=request.user)
        else:
            notifications = Notification.objects.all()

        # Filter by type
        notif_type = request.query_params.get("type")
        if notif_type:
            notifications = notifications.filter(type=notif_type)

        # Filter by read status
        is_read = request.query_params.get("is_read")
        if is_read is not None:
            notifications = notifications.filter(is_read=is_read.lower() == "true")

        # Pagination
        page = int(request.query_params.get("page", 1))
        page_size = int(request.query_params.get("page_size", 20))
        start = (page - 1) * page_size
        end = start + page_size

        total = notifications.count()
        unread_count = notifications.filter(is_read=False).count()

        serializer = NotificationSerializer(notifications[start:end], many=True)
        return Response({
            "count": total,
            "unread_count": unread_count,
            "page": page,
            "page_size": page_size,
            "results": serializer.data,
        })

    def post(self, request):
        serializer = NotificationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(
                user=request.user if request.user.is_authenticated else None
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class NotificationMarkReadAPIView(APIView):
    """
    PATCH /api/notifications/{id}/read/    → mark single notification as read
    """

    def patch(self, request, pk):
        notification = get_object_or_404(Notification, pk=pk)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(NotificationSerializer(notification).data)


class NotificationMarkAllReadAPIView(APIView):
    """
    POST /api/notifications/mark-all-read/   → mark all user's notifications as read
    """

    def post(self, request):
        if request.user.is_authenticated:
            updated = Notification.objects.filter(
                user=request.user, is_read=False
            ).update(is_read=True)
        else:
            updated = Notification.objects.filter(is_read=False).update(is_read=True)

        return Response({
            "message": f"{updated} notifications marked as read."
        })


class NotificationPreferenceAPIView(APIView):
    """
    GET  /api/notifications/preferences/   → get user's notification preferences
    PUT  /api/notifications/preferences/   → update preferences
    """

    def get(self, request):
        if request.user.is_authenticated:
            pref, created = NotificationPreference.objects.get_or_create(
                user=request.user
            )
        else:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(NotificationPreferenceSerializer(pref).data)

    def put(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        pref, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            pref, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
