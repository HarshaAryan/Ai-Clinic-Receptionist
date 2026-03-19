"""
ClinicOS — Reminder scheduler service.
Queries upcoming appointments and sends reminders via WhatsApp.
Designed to be called by APScheduler or a cron endpoint.
"""

from __future__ import annotations

from typing import Any, Dict, List

from agents.reminder import ReminderAgent
from db.queries import get_upcoming_appointments, get_clinic_by_id, log_message, find_or_create_patient, get_or_create_thread
from services.logger import logger
from services.whatsapp import send_whatsapp_msg


_reminder_agent = ReminderAgent()


def run_reminders_for_clinic(clinic_id: str, hours_before: int = 24) -> List[Dict[str, Any]]:
    """
    Check upcoming appointments for a clinic and send reminders.
    Returns a list of sent reminder summaries.
    """
    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        logger.warning("Reminder: clinic %s not found", clinic_id)
        return []

    appointments = get_upcoming_appointments(clinic_id, limit=50)
    if not appointments:
        return []

    reminders = _reminder_agent.build_reminders(
        appointments=appointments,
        clinic_name=clinic.get("name", "Clinic"),
        hours_before=hours_before,
    )

    sent: List[Dict[str, Any]] = []
    for reminder in reminders:
        try:
            send_whatsapp_msg(reminder.patient_phone, reminder.message)

            # Log the outbound reminder
            try:
                patient = find_or_create_patient(clinic_id, reminder.patient_phone)
                thread = get_or_create_thread(clinic_id, patient["id"], source="WHATSAPP")
                log_message(
                    clinic_id,
                    patient["id"],
                    thread["id"],
                    "TEXT",
                    "OUTBOUND",
                    f"[REMINDER] {reminder.message}",
                )
            except Exception as log_exc:
                logger.warning("Failed to log reminder: %s", log_exc)

            sent.append({
                "appointment_id": reminder.appointment_id,
                "patient_phone": reminder.patient_phone,
                "hours_before": reminder.hours_before,
                "status": "sent",
            })
            logger.info(
                "Reminder sent: clinic=%s appt=%s phone=%s",
                clinic_id, reminder.appointment_id, reminder.patient_phone,
            )
        except Exception as exc:
            logger.error("Failed to send reminder: %s", exc)
            sent.append({
                "appointment_id": reminder.appointment_id,
                "patient_phone": reminder.patient_phone,
                "hours_before": reminder.hours_before,
                "status": "failed",
                "error": str(exc),
            })

    return sent
