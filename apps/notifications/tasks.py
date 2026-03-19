"""
Celery Tasks for Notification Processing
"""
from celery import shared_task
from apps.notifications.models import Notification
from apps.notifications.managers import NotificationManager
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task
def send_notification_task(notification_id, channels):
    """
    Send notification through specified channels asynchronously.
    
    Args:
        notification_id: ID of notification to send
        channels: List of channel names (e.g., ["email", "sms"])
    """
    try:
        notification = Notification.objects.get(id=notification_id)
        NotificationManager._send_through_channels(notification, channels)
        logger.info(f"✅ Sent notification {notification_id} via {channels}")
    except Notification.DoesNotExist:
        logger.error(f"❌ Notification {notification_id} not found")
    except Exception as e:
        logger.error(f"❌ Failed to send notification {notification_id}: {e}")


@shared_task
def process_notification_queue():
    """
    Process pending notifications from queue.
    Runs every minute via Celery Beat (configured in settings.py).
    
    This is your CELERY_BEAT_SCHEDULE task.
    """
    logger.info("🔄 Processing notification queue...")
    
    # Example: Find notifications that need to be sent
    # You can add a 'scheduled_for' field to Notification model
    # and process notifications where scheduled_for <= now()
    
    pending_count = 0
    # Add your queue processing logic here
    
    logger.info(f"✅ Processed {pending_count} notifications")
    return pending_count


@shared_task
def send_appointment_reminders():
    """
    Send reminders for appointments happening in 24 hours.
    Run this task daily via Celery Beat.
    """
    from apps.appointments.models import Appointment
    from apps.notifications.triggers import notify_appointment_reminder
    
    tomorrow = timezone.now() + timedelta(days=1)
    start_of_day = tomorrow.replace(hour=0, minute=0, second=0)
    end_of_day = tomorrow.replace(hour=23, minute=59, second=59)
    
    appointments = Appointment.objects.filter(
        date=start_of_day.date(),
        status='CONFIRMED',
    )
    
    count = 0
    for appointment in appointments:
        notify_appointment_reminder(appointment)
        count += 1
    
    logger.info(f"✅ Sent {count} appointment reminders")
    return count


@shared_task
def send_prescription_refill_reminders():
    """
    Send reminders for prescriptions due for refill.
    Run this task daily.
    """
    from apps.pharmacy.models import Prescription
    from apps.notifications.triggers import notify_refill_reminder
    
    # Find prescriptions expiring in next 7 days
    week_from_now = timezone.now() + timedelta(days=7)
    
    prescriptions = Prescription.objects.filter(
        expiry_date__lte=week_from_now,
        expiry_date__gte=timezone.now(),
        refill_reminded=False,
    )
    
    count = 0
    for prescription in prescriptions:
        notify_refill_reminder(prescription)
        prescription.refill_reminded = True
        prescription.save(update_fields=['refill_reminded'])
        count += 1
    
    logger.info(f"✅ Sent {count} refill reminders")
    return count


@shared_task
def check_appointment_noshows():
    """
    Check for appointment no-shows (15 min late).
    Run this task every 15 minutes.
    """
    from apps.appointments.models import Appointment
    from apps.notifications.triggers import notify_appointment_noshow
    
    now = timezone.now()
    fifteen_min_ago = now - timedelta(minutes=15)
    
    # Find appointments that started 15+ minutes ago and are still "CONFIRMED"
    noshows = Appointment.objects.filter(
        datetime__lte=fifteen_min_ago,
        status='CONFIRMED',  # Status should be updated to IN_PROGRESS or COMPLETED
    )
    
    count = 0
    for appointment in noshows:
        # Mark as no-show
        appointment.status = 'NOSHOW'
        appointment.save(update_fields=['status'])
        
        # Notify staff
        if appointment.doctor and appointment.doctor.user:
            notify_appointment_noshow(appointment, appointment.doctor.user)
        
        count += 1
    
    logger.info(f"✅ Processed {count} no-shows")
    return count


@shared_task
def send_weekly_health_insights():
    """
    Send weekly AI-generated health insights to patients.
    Run this task weekly (e.g., every Monday at 9 AM).
    """
    from apps.patients.models import Patient
    from apps.notifications.triggers import notify_health_insight
    
    patients = Patient.objects.filter(
        user__isnull=False,
        preferences__health_insights=True,  # Only if opted in
    )
    
    count = 0
    for patient in patients:
        # Generate AI insight (you can integrate with your AI module)
        insight = f"This week: Your vitals are stable. Keep up with your medications!"
        notify_health_insight(patient, insight)
        count += 1
    
    logger.info(f"✅ Sent {count} health insights")
    return count


@shared_task
def cleanup_old_notifications():
    """
    Archive old read notifications (older than 30 days).
    Run this task daily to keep database clean.
    """
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    archived_count = Notification.objects.filter(
        is_read=True,
        created_at__lt=thirty_days_ago,
        is_archived=False,
    ).update(is_archived=True)
    
    logger.info(f"✅ Archived {archived_count} old notifications")
    return archived_count


# ═══════════════════════════════════════════════════════════════════════════════
# ADD THESE TASKS TO CELERY BEAT SCHEDULE IN settings.py:
# ═══════════════════════════════════════════════════════════════════════════════
"""
CELERY_BEAT_SCHEDULE = {
    'process-notification-queue': {
        'task': 'apps.notifications.tasks.process_notification_queue',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
    'send-appointment-reminders': {
        'task': 'apps.notifications.tasks.send_appointment_reminders',
        'schedule': crontab(hour=9, minute=0),  # Daily at 9 AM
    },
    'check-appointment-noshows': {
        'task': 'apps.notifications.tasks.check_appointment_noshows',
        'schedule': crontab(minute='*/15'),  # Every 15 minutes
    },
    'send-prescription-refills': {
        'task': 'apps.notifications.tasks.send_prescription_refill_reminders',
        'schedule': crontab(hour=10, minute=0),  # Daily at 10 AM
    },
    'send-health-insights': {
        'task': 'apps.notifications.tasks.send_weekly_health_insights',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),  # Monday 9 AM
    },
    'cleanup-old-notifications': {
        'task': 'apps.notifications.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
    },
}
"""