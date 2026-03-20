"""
Notification Triggers - Helper functions to trigger notifications from different modules

Based on your notification flow table, these functions should be called from:
- apps/appointments/views.py or signals.py
- apps/billing/views.py or signals.py  
- apps/labs/views.py or signals.py
- apps/pharmacy/views.py or signals.py
- etc.
"""
from apps.notifications.managers import NotificationManager
from typing import Optional
import logging

logger = logging.getLogger(__name__)
# ═══════════════════════════════════════════════════════════════════════════════
# APPOINTMENTS MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_appointment_confirmation(appointment):
    """
    Trigger: Send notification to DOCTOR when appointment is booked
    (Not patient - most patients don't have user accounts)
    """
    logger.info(f"🔔 notify_appointment_confirmation called for appointment {appointment.id}")
    logger.info(f"   Patient: {appointment.patient_name}")
    logger.info(f"   Doctor: {appointment.doctor.name}")
    
    # Send to DOCTOR (not patient!)
    if not appointment.doctor:
        logger.warning(f"⚠️ No doctor assigned")
        return
    
    if not hasattr(appointment.doctor, 'user'):
        logger.warning(f"⚠️ Doctor has no 'user' attribute")
        return
    
    if not appointment.doctor.user:
        logger.warning(f"⚠️ Doctor {appointment.doctor.name} has no user account")
        return
    
    doctor_user = appointment.doctor.user
    logger.info(f"✅ Sending notification to doctor: {doctor_user.email}")
    
    try:
        NotificationManager.send(
            user=doctor_user,
            notification_type="new_appointment_booking",
            title="📅 New Appointment Booked",
            body=f"New appointment: {appointment.patient_name or appointment.patient.full_name} on {appointment.appointment_date.strftime('%b %d, %Y')} at {appointment.appointment_time.strftime('%I:%M %p')}",
            channels=["inapp"],
            priority="medium",
            action_url=f"/dashboard/appointments/{appointment.id}/",
            action_text="View Appointment",
            metadata={
                "appointment_id": str(appointment.id),
                "patient_name": appointment.patient_name or str(appointment.patient),
            }
        )
        logger.info(f"✅✅✅ SUCCESS: Notification created for {doctor_user.email}")
        
    except Exception as e:
        logger.error(f"❌ Failed to create notification: {e}")
        import traceback
        logger.error(traceback.format_exc())

        
def notify_appointment_reminder(appointment):
    """Trigger: 24 hours before appointment"""
    NotificationManager.send(
        user=appointment.patient.user,
        notification_type="appointment_reminder",
        title="Appointment Reminder",
        body=f"Reminder: You have an appointment tomorrow at {appointment.time} with Dr. {appointment.doctor.name}",
        channels=["sms", "whatsapp"],  # Priority channels for reminders
        priority="high",
        action_url=f"/appointments/{appointment.id}/",
        metadata={"appointment_id": str(appointment.id)}
    )


def notify_appointment_rescheduled(appointment, old_date, old_time):
    """Trigger: Staff reschedules appointment"""
    NotificationManager.send(
        user=appointment.patient.user,
        notification_type="appointment_reschedule",
        title="Appointment Rescheduled",
        body=f"Your appointment has been rescheduled from {old_date} {old_time} to {appointment.date} {appointment.time}",
        channels=["inapp", "email", "sms", "whatsapp"],
        priority="high",
        action_url=f"/appointments/{appointment.id}/",
        metadata={
            "appointment_id": str(appointment.id),
            "old_date": str(old_date),
            "new_date": str(appointment.date),
        }
    )


def notify_appointment_cancelled(appointment, reason: str = ""):
    """Trigger: Appointment cancelled"""
    NotificationManager.send(
        user=appointment.patient.user,
        notification_type="appointment_cancellation",
        title="Appointment Cancelled",
        body=f"Your appointment on {appointment.date} at {appointment.time} has been cancelled. {reason}",
        channels=["inapp", "email", "sms", "whatsapp"],
        priority="high",
        metadata={"appointment_id": str(appointment.id), "reason": reason}
    )


def notify_appointment_noshow(appointment, staff_user):
    """Trigger: Patient no-show (15 min late)"""
    NotificationManager.send(
        user=staff_user,
        notification_type="appointment_noshow_alert",
        title="Patient No-Show Alert",
        body=f"Patient {appointment.patient.name} did not show up for appointment at {appointment.time}",
        channels=["inapp"],  # Staff only
        priority="medium",
        action_url=f"/appointments/{appointment.id}/",
        metadata={"appointment_id": str(appointment.id), "patient_id": str(appointment.patient.id)}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BILLING MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_invoice_ready(invoice):
    """Trigger: Invoice generated"""
    NotificationManager.send(
        user=invoice.patient.user,
        notification_type="invoice_ready",
        title="Invoice Ready",
        body=f"Your invoice #{invoice.invoice_number} for ₹{invoice.total_amount} is ready",
        channels=["inapp", "email"],
        priority="medium",
        action_url=f"/billing/{invoice.id}/",
        action_text="View Invoice",
        metadata={"invoice_id": str(invoice.id), "amount": str(invoice.total_amount)}
    )


def notify_payment_received(payment):
    """Trigger: Payment successful"""
    NotificationManager.send(
        user=payment.patient.user,
        notification_type="payment_received",
        title="Payment Received",
        body=f"We received your payment of ₹{payment.amount}. Thank you!",
        channels=["inapp", "email", "sms", "whatsapp"],
        priority="medium",
        action_url=f"/billing/{payment.invoice.id}/",
        action_text="View Receipt",
        metadata={"payment_id": str(payment.id), "amount": str(payment.amount)}
    )


def notify_insurance_claim_update(claim, status):
    """Trigger: Insurance claim status change"""
    NotificationManager.send(
        user=claim.patient.user,
        notification_type="insurance_claim_update",
        title="Insurance Claim Update",
        body=f"Your insurance claim status: {status}",
        channels=["inapp", "email"],
        priority="medium",
        action_url=f"/billing/claims/{claim.id}/",
        metadata={"claim_id": str(claim.id), "status": status}
    )


def notify_refund_processed(refund):
    """Trigger: Refund approved and processed"""
    NotificationManager.send(
        user=refund.patient.user,
        notification_type="refund_processed",
        title="Refund Processed",
        body=f"Your refund of ₹{refund.amount} has been processed and will reflect in 5-7 business days",
        channels=["inapp", "email", "sms"],
        priority="high",
        metadata={"refund_id": str(refund.id), "amount": str(refund.amount)}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# LAB MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_lab_results_ready(lab_order):
    """Trigger: Lab results uploaded (URGENT)"""
    NotificationManager.send(
        user=lab_order.patient.user,
        notification_type="lab_results_ready",
        title="Lab Results Ready",
        body=f"Your lab test results are ready. Please check your patient portal.",
        channels=["inapp", "email", "sms", "whatsapp"],  # All channels
        priority="urgent",
        action_url=f"/lab/results/{lab_order.id}/",
        action_text="View Results",
        metadata={"lab_order_id": str(lab_order.id)}
    )


def notify_sample_collected(lab_order):
    """Trigger: Sample collected from patient"""
    NotificationManager.send(
        user=lab_order.patient.user,
        notification_type="sample_collected",
        title="Sample Collected",
        body=f"Your sample has been collected. Results will be available in {lab_order.turnaround_time} hours.",
        channels=["inapp"],
        priority="low",
        metadata={"lab_order_id": str(lab_order.id)}
    )


def notify_test_reminder(lab_order):
    """Trigger: Scheduled test reminder"""
    NotificationManager.send(
        user=lab_order.patient.user,
        notification_type="test_reminder",
        title="Lab Test Reminder",
        body=f"Reminder: Your lab test is scheduled for {lab_order.scheduled_date}",
        channels=["sms", "whatsapp"],
        priority="medium",
        metadata={"lab_order_id": str(lab_order.id)}
    )


def notify_critical_lab_alert(lab_order, abnormal_values):
    """Trigger: Critical/abnormal lab values detected"""
    # Notify patient
    NotificationManager.send(
        user=lab_order.patient.user,
        notification_type="critical_lab_alert",
        title="⚠️ Critical Lab Result",
        body="Your lab results show abnormal values. Please contact your doctor immediately.",
        channels=["inapp", "email", "sms", "whatsapp"],  # All channels + call
        priority="urgent",
        action_url=f"/lab/results/{lab_order.id}/",
        metadata={"lab_order_id": str(lab_order.id), "abnormal_values": abnormal_values}
    )
    
    # Also notify doctor
    if lab_order.doctor:
        NotificationManager.send(
            user=lab_order.doctor.user,
            notification_type="critical_lab_alert_doctor",
            title="⚠️ Patient Critical Lab Result",
            body=f"Patient {lab_order.patient.name} has critical lab values requiring immediate attention",
            channels=["inapp", "sms"],
            priority="urgent",
            action_url=f"/lab/results/{lab_order.id}/",
        )


# ═══════════════════════════════════════════════════════════════════════════════
# PRESCRIPTIONS MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_new_prescription(prescription):
    """Trigger: New prescription issued"""
    NotificationManager.send(
        user=prescription.patient.user,
        notification_type="new_prescription",
        title="New Prescription Issued",
        body=f"Dr. {prescription.doctor.name} has issued a new prescription for you",
        channels=["inapp", "whatsapp"],
        priority="medium",
        action_url=f"/prescriptions/{prescription.id}/",
        action_text="View Prescription",
        metadata={"prescription_id": str(prescription.id)}
    )


def notify_refill_reminder(prescription):
    """Trigger: Prescription refill due"""
    NotificationManager.send(
        user=prescription.patient.user,
        notification_type="refill_reminder",
        title="Prescription Refill Reminder",
        body=f"Your prescription is due for refill. Please contact your pharmacy.",
        channels=["sms", "email"],
        priority="medium",
        action_url=f"/prescriptions/{prescription.id}/",
        metadata={"prescription_id": str(prescription.id)}
    )


def notify_prescription_expiry(prescription, days_left):
    """Trigger: Prescription expiring soon (7 days)"""
    NotificationManager.send(
        user=prescription.patient.user,
        notification_type="prescription_expiry_alert",
        title="Prescription Expiring Soon",
        body=f"Your prescription will expire in {days_left} days. Please consult your doctor for renewal.",
        channels=["inapp"],
        priority="low",
        metadata={"prescription_id": str(prescription.id), "days_left": days_left}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# AI FEATURES MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_ai_followup_detected(patient, analysis_data):
    """Trigger: AI detected follow-up needed"""
    NotificationManager.send(
        user=patient.user,
        notification_type="ai_followup_detected",
        title="Follow-up Recommended",
        body="Based on your recent visit, a follow-up appointment is recommended",
        channels=["whatsapp", "sms"],
        priority="medium",
        action_url="/appointments/book/",
        action_text="Book Follow-up",
        metadata={"patient_id": str(patient.id), "ai_analysis": analysis_data}
    )


def notify_noshow_risk(appointment, risk_score, staff_user):
    """Trigger: AI predicts high no-show risk"""
    NotificationManager.send(
        user=staff_user,
        notification_type="noshow_risk_alert",
        title="No-Show Risk Alert",
        body=f"Patient {appointment.patient.name} has {risk_score}% no-show risk for appointment on {appointment.date}",
        channels=["inapp"],  # Staff only
        priority="medium",
        action_url=f"/appointments/{appointment.id}/",
        metadata={"appointment_id": str(appointment.id), "risk_score": risk_score}
    )


def notify_triage_recommendation(patient, symptoms, recommendation):
    """Trigger: AI symptom checker provides triage"""
    NotificationManager.send(
        user=patient.user,
        notification_type="triage_recommendation",
        title="Health Assessment Complete",
        body=f"Based on your symptoms: {recommendation}",
        channels=["inapp", "whatsapp"],
        priority="high",
        action_url="/ai/triage/",
        metadata={"patient_id": str(patient.id), "symptoms": symptoms}
    )


def notify_health_insight(patient, insight_text):
    """Trigger: Weekly AI health insights"""
    NotificationManager.send(
        user=patient.user,
        notification_type="health_insight",
        title="Your Weekly Health Insight",
        body=insight_text,
        channels=["email"],
        priority="low",
        metadata={"patient_id": str(patient.id)}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# STAFF MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_task_assigned(task, staff_user):
    """Trigger: Task assigned to staff member"""
    NotificationManager.send(
        user=staff_user,
        notification_type="task_assigned",
        title="New Task Assigned",
        body=f"You have been assigned: {task.title}",
        channels=["inapp", "email"],
        priority="medium",
        action_url=f"/tasks/{task.id}/",
        action_text="View Task",
        metadata={"task_id": str(task.id)}
    )


def notify_schedule_change(staff_user, old_schedule, new_schedule):
    """Trigger: Staff schedule updated"""
    NotificationManager.send(
        user=staff_user,
        notification_type="schedule_change",
        title="Schedule Updated",
        body=f"Your schedule has been updated. Please review the changes.",
        channels=["inapp", "sms"],
        priority="high",
        action_url="/schedule/",
        metadata={"old": str(old_schedule), "new": str(new_schedule)}
    )


def notify_leave_approval(leave_request, approved: bool):
    """Trigger: Leave request approved/rejected"""
    status = "approved" if approved else "rejected"
    NotificationManager.send(
        user=leave_request.staff.user,
        notification_type="leave_approval",
        title=f"Leave Request {status.title()}",
        body=f"Your leave request for {leave_request.start_date} to {leave_request.end_date} has been {status}",
        channels=["inapp"],
        priority="medium",
        action_url=f"/leave/{leave_request.id}/",
        metadata={"leave_id": str(leave_request.id), "status": status}
    )


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM MODULE
# ═══════════════════════════════════════════════════════════════════════════════

def notify_security_alert(user, alert_type, details):
    """Trigger: Suspicious activity detected"""
    NotificationManager.send(
        user=user,
        notification_type="security_alert",
        title="⚠️ Security Alert",
        body=f"Unusual activity detected: {alert_type}. {details}",
        channels=["inapp", "email", "sms"],
        priority="urgent",
        action_url="/security/",
        metadata={"alert_type": alert_type, "details": details}
    )


def notify_tenant_update(tenant_admin, update_message):
    """Trigger: Admin action on tenant"""
    NotificationManager.send(
        user=tenant_admin,
        notification_type="tenant_update",
        title="Platform Update",
        body=update_message,
        channels=["inapp", "email"],
        priority="medium",
        metadata={}
    )


def notify_maintenance_scheduled(user, maintenance_window):
    """Trigger: Scheduled maintenance"""
    NotificationManager.send(
        user=user,
        notification_type="maintenance_scheduled",
        title="Scheduled Maintenance",
        body=f"System maintenance is scheduled for {maintenance_window}. Services may be temporarily unavailable.",
        channels=["inapp"],  # In-app banner
        priority="low",
        metadata={"window": maintenance_window}
    )