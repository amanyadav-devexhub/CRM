from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Notification, NotificationPreference
from .serializers import NotificationSerializer, NotificationPreferenceSerializer
from .utils import mark_notification_as_read, get_unread_count

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for viewing notifications"""
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """Mark a notification as read"""
        success = mark_notification_as_read(pk, request.user)
        if success:
            return Response({'status': 'marked as read'})
        return Response({'error': 'Notification not found'}, status=404)
    
    @action(detail=False, methods=['post'])
    def mark_all_read(self, request):
        """Mark all notifications as read"""
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True
        )
        return Response({'status': 'all marked as read'})
    
    @action(detail=False, methods=['get'])
    def unread_count(self, request):
        """Get unread count"""
        count = get_unread_count(request.user)
        return Response({'count': count})
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        """Get recent notifications (last 10)"""
        notifications = self.get_queryset()[:10]
        serializer = self.get_serializer(notifications, many=True)
        return Response(serializer.data)


class NotificationPreferenceViewSet(viewsets.ModelViewSet):
    """ViewSet for managing notification preferences"""
    serializer_class = NotificationPreferenceSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return NotificationPreference.objects.filter(user=self.request.user)
    
    def get_or_create(self, request):
        """Get or create preferences for current user"""
        pref, created = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = self.get_serializer(pref)
        return Response(serializer.data)
    
    # In your appointment creation view
from apps.notifications.utils import send_notification

def book_appointment(request):
    # ... your booking logic
    
    # Send notification
    send_notification(
        user=patient,
        notification_type='appointment_confirmation',
        title='Appointment Confirmed',
        body=f"Your appointment with Dr. {doctor.name} is confirmed for {appointment.date}",
        channel_priority=['whatsapp', 'sms', 'email', 'in_app'],
        metadata={
            'patient_name': patient.get_full_name(),
            'doctor_name': doctor.name,
            'date': appointment.date.strftime('%B %d, %Y'),
            'time': appointment.time.strftime('%I:%M %p'),
            'clinic_name': request.tenant.name
        },
        action_url=f"/appointments/{appointment.id}",
        tenant=request.tenant
    )