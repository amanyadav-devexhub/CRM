"""
Celery tasks for the Communications app.

These are stub implementations that define the task signatures.
Integrate with actual messaging providers (Twilio, WhatsApp Business API,
SendGrid) when ready.
"""

import logging

logger = logging.getLogger(__name__)


def send_message_task(message_id):
    """
    Send a single message via its configured channel.
    Retrieves the Message record, dispatches to the appropriate provider,
    and updates the status to 'sent' or 'failed'.
    """
    from .models import Message
    from django.utils import timezone

    try:
        message = Message.objects.get(pk=message_id)

        # ── Provider dispatch placeholder ──
        # if message.channel == "email":
        #     send_email(message.patient.email, message.subject, message.body)
        # elif message.channel == "sms":
        #     send_sms(message.patient.phone, message.body)
        # elif message.channel == "whatsapp":
        #     send_whatsapp(message.patient.phone, message.body)

        message.status = "sent"
        message.sent_at = timezone.now()
        message.save(update_fields=["status", "sent_at"])

        logger.info(f"Message {message_id} sent via {message.channel}")

    except Message.DoesNotExist:
        logger.error(f"Message {message_id} not found")
    except Exception as e:
        logger.error(f"Failed to send message {message_id}: {e}")
        Message.objects.filter(pk=message_id).update(
            status="failed", error_message=str(e)
        )


def send_campaign_messages(campaign_id):
    """
    Batch-process a campaign: resolve the patient segment,
    create individual Message records, and queue them for sending.
    """
    from .models import Campaign, Message
    from apps.patients.models import Patient

    try:
        campaign = Campaign.objects.get(pk=campaign_id)

        if campaign.status != "scheduled":
            logger.warning(f"Campaign {campaign_id} is not in 'scheduled' state")
            return

        campaign.status = "running"
        campaign.save(update_fields=["status"])

        # ── Build patient queryset from segment_filter ──
        patients = Patient.objects.all()
        filters = campaign.segment_filter or {}

        if "tags" in filters:
            patients = patients.filter(tags__name__in=filters["tags"])
        if "gender" in filters:
            patients = patients.filter(gender=filters["gender"])

        recipient_list = patients.distinct()
        campaign.total_recipients = recipient_list.count()

        sent = 0
        failed = 0

        for patient in recipient_list:
            try:
                Message.objects.create(
                    patient=patient,
                    template=campaign.template,
                    channel=campaign.template.channel if campaign.template else "email",
                    subject=campaign.template.subject if campaign.template else "",
                    body=campaign.template.body if campaign.template else "",
                    status="queued",
                )
                sent += 1
            except Exception as e:
                logger.error(f"Failed to create message for patient {patient.id}: {e}")
                failed += 1

        campaign.sent_count = sent
        campaign.failed_count = failed
        campaign.status = "completed"
        campaign.save(update_fields=[
            "total_recipients", "sent_count", "failed_count", "status"
        ])

        logger.info(
            f"Campaign '{campaign.name}' completed: "
            f"{sent} sent, {failed} failed out of {campaign.total_recipients}"
        )

    except Campaign.DoesNotExist:
        logger.error(f"Campaign {campaign_id} not found")
