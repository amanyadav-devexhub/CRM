from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from apps.notifications.models import Notification
from apps.notifications.serializers import (
    NotificationSerializer,
    NotificationListSerializer,
    NotificationMarkReadSerializer
)


class NotificationListView(generics.ListAPIView):
    """
    List notifications for current user.
    Supports filtering by is_read and limiting results.
    """
    serializer_class = NotificationListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        queryset = Notification.objects.filter(
            user=user,
            is_archived=False
        ).select_related('user').order_by('-created_at')
        
        # Filter by read status
        is_read = self.request.query_params.get('is_read')
        if is_read is not None:
            queryset = queryset.filter(is_read=is_read.lower() == 'true')
        
        # Limit results
        limit = self.request.query_params.get('limit')
        if limit:
            try:
                queryset = queryset[:int(limit)]
            except (ValueError, TypeError):
                pass
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Override to include count in response"""
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        # Get unread count
        unread_count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_archived=False
        ).count()
        
        return Response({
            'results': serializer.data,
            'count': unread_count
        })


class MarkAsReadView(APIView):
    """
    Mark a single notification as read.
    POST /api/notifications/{uuid}/mark-read/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                id=pk,
                user=request.user
            )
            notification.mark_as_read()
            
            return Response({
                'success': True,
                'message': 'Notification marked as read'
            })
        except Notification.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Notification not found'
            }, status=status.HTTP_404_NOT_FOUND)


class MarkAllAsReadView(APIView):
    """
    Mark all notifications as read for current user.
    POST /api/notifications/mark-all-read/
    """
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        updated_count = Notification.objects.filter(
            user=request.user,
            is_read=False,
            is_archived=False
        ).update(is_read=True)
        
        return Response({
            'success': True,
            'message': f'{updated_count} notifications marked as read',
            'count': updated_count
        })


class NotificationDetailView(generics.RetrieveAPIView):
    """
    Get details of a single notification.
    GET /api/notifications/{uuid}/
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)