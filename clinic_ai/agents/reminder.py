"""
Reminder Agent (NudgeBot) — sends appointment reminders
24 hours and 2 hours before, plus post-visit follow-ups.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List

from agents.base_agent import AgentResult, BaseAgent
from models import IncomingMessage, ReminderPayload
from services.gemini import generate_reminder_message
from services.logger import logger


class ReminderAgent(BaseAgent):
    """
    Generates reminder messages for upcoming appointments.
    Typically called by the scheduler, not directly from the orchestrator.
    """

    name = "ReminderAgent"

    # ── BaseAgent interface (not typically used for reminders) ─

    def handle(self, message: IncomingMessage, context: Dict[str, Any]) -> AgentResult:
        """Not the primary entry — reminders are triggered by cron, not user messages."""
        return AgentResult(
            reply_text="Thank you for your message! Our team will follow up shortly.",
            action="none",
        )

    # ── Main entry: called by the scheduler ─────────────────

    def build_reminders(
        self,
        appointments: List[Dict[str, Any]],
        clinic_name: str,
        hours_before: int = 24,
    ) -> List[ReminderPayload]:
        """
        Given a list of upcoming appointments, build reminder payloads
        for those within the `hours_before` window.
        """
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours_before)
        reminders: List[ReminderPayload] = []

        for appt in appointments:
            start = appt.get("start_time")
            if not isinstance(start, datetime):
                continue

            # Only remind if appointment is between now and cutoff
            if not (now < start <= cutoff):
                continue

            patient_name = appt.get("patient_name", "Patient")
            patient_phone = appt.get("patient_phone")
            if not patient_phone:
                continue

            # Generate friendly message via Gemini
            try:
                msg = generate_reminder_message(
                    patient_name=patient_name,
                    clinic_name=clinic_name,
                    appointment_time=start.strftime("%d %b %Y at %I:%M %p"),
                    hours_before=hours_before,
                )
            except Exception as exc:
                logger.warning("Gemini reminder gen failed, using template: %s", exc)
                msg = (
                    f"Hi {patient_name}! 🏥 Reminder: You have an appointment at "
                    f"{clinic_name} on {start.strftime('%d %b at %I:%M %p')}. "
                    f"Please arrive 10 minutes early. Reply CANCEL to cancel."
                )

            reminders.append(
                ReminderPayload(
                    appointment_id=str(appt.get("id", "")),
                    patient_id=str(appt.get("patient_id", "")),
                    patient_phone=patient_phone,
                    patient_name=patient_name,
                    appointment_time=start,
                    clinic_name=clinic_name,
                    hours_before=hours_before,
                    message=msg,
                )
            )

        logger.info("Built %d reminders (%dh window) for %s", len(reminders), hours_before, clinic_name)
        return reminders

    def build_followup_message(self, patient_name: str, clinic_name: str) -> str:
        """Post-visit follow-up message."""
        try:
            return generate_reminder_message(
                patient_name=patient_name,
                clinic_name=clinic_name,
                appointment_time="(completed)",
                hours_before=0,
            )
        except Exception:
            return (
                f"Hi {patient_name}! Thank you for visiting {clinic_name} today. "
                f"We hope you're feeling better. If you have any questions, reply here. 😊"
            )
