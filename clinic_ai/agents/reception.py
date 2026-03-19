"""
Reception Agent (ReceptBot) — handles appointment booking, rescheduling,
cancellation, general queries, and follow-ups.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any, Dict

import dateparser

from agents.base_agent import AgentResult, BaseAgent
from db.queries import (
    create_appointment,
    get_clinic_google_tokens,
    update_appointment_calendar_id,
)
from models import IncomingMessage, IntentType
from services.calendar import create_event, get_free_busy
from services.gemini import reception_reply
from services.logger import logger


class ReceptionAgent(BaseAgent):
    """
    AI Receptionist — answers patient queries, books appointments,
    handles rescheduling and FAQ.
    """

    name = "ReceptionAgent"

    def handle(self, message: IncomingMessage, context: Dict[str, Any]) -> AgentResult:
        clinic = context.get("clinic", {})
        patient = context.get("patient", {})
        classification = context.get("classification")
        kb_text = context.get("kb_text", "")
        history_text = context.get("history_text", "")
        slots_text = context.get("slots_text", "(No slots checked yet.)")

        intent = classification.intent if classification else IntentType.GENERAL_QUERY

        # ── Try to detect a desired time & book ─────────────
        if intent in (IntentType.APPOINTMENT_BOOK, IntentType.APPOINTMENT_RESCHEDULE):
            slots_text = self._handle_booking(message, context, clinic, patient)

        # ── Build the user prompt with conversation context ─
        user_text = f"Conversation Context:\n{history_text}\n\nUser: {message.text}"

        # ── Get Gemini reply ────────────────────────────────
        raw_reply = reception_reply(
            user_text=user_text,
            clinic_name=clinic.get("name", "Clinic"),
            doctor_name=clinic.get("doctor_name", "Doctor"),
            specialty=clinic.get("specialization", "General"),
            working_hours=context.get("working_hours", "Mon-Fri, 10 AM – 6 PM"),
            services_list=context.get("services_list", "General consultation"),
            fees=context.get("fees", "As per consultation"),
            kb_text=kb_text,
            slots_text=slots_text,
            patient_history=history_text,
            classified_intent=intent.value,
        )

        # Parse structured JSON if Gemini returned it
        reply_text, action, appt_details = self._parse_reply(raw_reply)

        return AgentResult(
            reply_text=reply_text,
            action=action,
            data={"appointment_details": appt_details, "intent": intent.value},
        )

    # ── Internal helpers ────────────────────────────────────

    def _handle_booking(
        self,
        message: IncomingMessage,
        context: Dict[str, Any],
        clinic: Dict[str, Any],
        patient: Dict[str, Any],
    ) -> str:
        """Attempt to parse a date/time and book against Google Calendar."""
        desired_time = dateparser.parse(
            message.text,
            settings={"PREFER_DATES_FROM": "future"},
        )
        if not desired_time:
            return "(Could not detect a date/time from the message. Ask the patient to specify.)"

        tokens = get_clinic_google_tokens(clinic.get("id"))
        if not tokens:
            return f"Requested time: {desired_time.strftime('%Y-%m-%d %H:%M')}. (Calendar not connected — cannot verify availability.)"

        slot_minutes = context.get("slot_duration_minutes", 30)
        end_time = desired_time + timedelta(minutes=slot_minutes)

        try:
            busy = get_free_busy(tokens, desired_time, end_time)
        except Exception as exc:
            logger.warning("Free/busy check failed: %s", exc)
            return "(Calendar check failed. Ask the patient to call the clinic.)"

        if busy:
            return "Requested slot is busy. Ask for another time within clinic hours."

        # Book
        try:
            clinic_id = clinic["id"]
            appt = create_appointment(clinic_id, patient["id"], desired_time, status="PENDING")
            event_id = create_event(
                tokens,
                desired_time,
                end_time,
                summary=f"Appointment – {clinic.get('name', 'Clinic')}",
                description=f"Patient phone: {message.sender_phone} | Source: {message.channel.value}",
            )
            update_appointment_calendar_id(clinic_id, appt["id"], event_id, status="CONFIRMED")
            return f"Slot at {desired_time.strftime('%Y-%m-%d %H:%M')} is available and BOOKED ✅."
        except Exception as exc:
            logger.error("Appointment creation failed: %s", exc)
            return "(Slot might be taken — appointment could not be created.)"

    @staticmethod
    def _parse_reply(raw: str):
        """Try to extract JSON from Gemini output; fall back to plain text."""
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            data = json.loads(cleaned.strip())
            return (
                data.get("reply", raw),
                data.get("action", "none"),
                data.get("appointment_details"),
            )
        except (json.JSONDecodeError, AttributeError):
            return raw, "none", None
