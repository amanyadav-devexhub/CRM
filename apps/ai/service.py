from apps.notifications.triggers import notify_noshow_risk

def analyze_appointment_risk(appointment):
    # AI model predicts no-show probability
    risk_score = predict_noshow_probability(appointment)
    
    if risk_score > 70:  # High risk
        # ✅ TRIGGER 2: Alert staff about risk
        staff_users = get_clinic_staff(appointment.clinic)
        for staff in staff_users:
            notify_noshow_risk(appointment, risk_score, staff)