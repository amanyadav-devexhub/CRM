"""
Celery tasks for the Notifications app.

These are stub implementations that define the task signatures.
Wire to Celery Beat or call directly when the trigger event occurs.
"""

import logging

logger = logging.getLogger(__name__)


def send_appointment_reminder(appointment_id):
    """
    Send reminder notifications 24h and 1h before an appointment.
    Creates in-app Notification + triggers message via Communications.
    """
    from .models import Notification
    from apps.appointments.models import Appointment

    try:
        appointment = Appointment.objects.select_related("doctor").get(pk=appointment_id)

        Notification.objects.create(
            user_id=None,  # TODO: resolve from patient → user FK
            type="appointment",
            title="Appointment Reminder",
            body=(
                f"You have an appointment with Dr. {appointment.doctor.name} "
                f"on {appointment.appointment_date} at {appointment.appointment_time}."
            ),
            action_url=f"/appointments/{appointment.id}/",
        )
        logger.info(f"Appointment reminder sent for {appointment_id}")

    except Appointment.DoesNotExist:
        logger.error(f"Appointment {appointment_id} not found")
    except Exception as e:
        logger.error(f"Failed to send appointment reminder: {e}")


def send_follow_up_reminder(patient_id, appointment_id=None):
    """
    Send a follow-up reminder after a completed visit.
    Typically triggered 3-7 days post-appointment.
    """
    from .models import Notification

    try:
        Notification.objects.create(
            user_id=None,  # TODO: resolve from patient → user FK
            type="appointment",
            title="Follow-Up Reminder",
            body="It's time for your follow-up visit. Please schedule an appointment.",
            action_url="/appointments/",
        )
        logger.info(f"Follow-up reminder sent for patient {patient_id}")

    except Exception as e:
        logger.error(f"Failed to send follow-up reminder: {e}")


def send_payment_reminder(invoice_id):
    """
    Send a payment reminder for overdue invoices.
    """
    from .models import Notification

    try:
        Notification.objects.create(
            user_id=None,  # TODO: resolve from invoice → patient → user FK
            type="billing",
            title="Payment Reminder",
            body="You have an overdue invoice. Please make your payment at your earliest convenience.",
            action_url=f"/billing/invoices/{invoice_id}/",
        )
        logger.info(f"Payment reminder sent for invoice {invoice_id}")

    except Exception as e:
        logger.error(f"Failed to send payment reminder: {e}")


def send_lab_result_notification(lab_order_id):
    """
    Notify a patient when their lab results are ready.
    """
    from .models import Notification

    try:
        Notification.objects.create(
            user_id=None,  # TODO: resolve from lab order → patient → user FK
            type="lab",
            title="Lab Results Ready",
            body="Your lab test results are now available. Please check your reports.",
            action_url=f"/labs/results/{lab_order_id}/",
        )
        logger.info(f"Lab result notification sent for order {lab_order_id}")

    except Exception as e:
        logger.error(f"Failed to send lab result notification: {e}")
