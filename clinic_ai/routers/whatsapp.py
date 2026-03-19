"""
ClinicOS — WhatsApp webhook router.
Uses the Orchestrator → Agent pipeline for every inbound message.
"""

import os
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from agents.emergency import EmergencyAgent
from agents.orchestrator import Orchestrator
from agents.reception import ReceptionAgent
from agents.reminder import ReminderAgent
from db.queries import (
    find_or_create_patient,
    get_clinic_by_phone_id,
    get_clinic_settings,
    get_kb_entries,
    get_last_messages,
    get_or_create_thread,
    is_thread_takeover_enabled,
    log_message,
)
from models import ChannelSource, IncomingMessage, IntentType
from services.kb import render_kb
from services.logger import logger
from services.slots import format_slots_text, generate_available_slots
from services.whatsapp import send_whatsapp_msg

router = APIRouter()

# ── Build the orchestrator singleton ────────────────────────

_orchestrator: Optional[Orchestrator] = None


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()

        reception = ReceptionAgent()
        emergency = EmergencyAgent()
        reminder = ReminderAgent()

        # Reception handles most intents
        _orchestrator.register(IntentType.APPOINTMENT_BOOK, reception)
        _orchestrator.register(IntentType.APPOINTMENT_RESCHEDULE, reception)
        _orchestrator.register(IntentType.APPOINTMENT_CANCEL, reception)
        _orchestrator.register(IntentType.GENERAL_QUERY, reception)
        _orchestrator.register(IntentType.FOLLOWUP, reception)
        _orchestrator.register(IntentType.UNKNOWN, reception)

        # Emergency gets its own handler
        _orchestrator.register(IntentType.EMERGENCY, emergency)

        logger.info("Orchestrator initialized with agents")

    return _orchestrator


# ── Payload helpers ─────────────────────────────────────────


def _extract_payload(data: dict):
    entry = (data.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    return changes.get("value") or {}


def _extract_phone_id(value: dict) -> Optional[str]:
    return (value.get("metadata") or {}).get("phone_number_id")


def _extract_message(value: dict) -> Optional[dict]:
    messages = value.get("messages") or []
    if not messages:
        return None
    msg = messages[0]
    return {
        "from": msg.get("from"),
        "text": (msg.get("text") or {}).get("body"),
    }


# ── Endpoints ───────────────────────────────────────────────


@router.get("/webhook/whatsapp")
async def verify_whatsapp_webhook(request: Request):
    verify_token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if verify_token and verify_token == os.getenv("VERIFY_TOKEN") and challenge:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Verification failed", status_code=403)


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    value = _extract_payload(data)
    phone_id = _extract_phone_id(value)
    message = _extract_message(value)

    if not phone_id or not message or not message.get("text"):
        return JSONResponse({"status": "ignored"}, status_code=200)

    # ── Resolve clinic ──────────────────────────────────────
    clinic = get_clinic_by_phone_id(phone_id)
    if not clinic:
        logger.warning("Unknown clinic for phone_id=%s", phone_id)
        return JSONResponse({"status": "unknown_clinic"}, status_code=200)

    clinic_id = str(clinic["id"])
    sender_phone = message["from"]
    text = message["text"]

    # ── Resolve patient & thread ────────────────────────────
    patient = find_or_create_patient(clinic_id, sender_phone)
    thread = get_or_create_thread(clinic_id, patient["id"], source="WHATSAPP")

    log_message(clinic_id, patient["id"], thread["id"], "TEXT", "INBOUND", text)

    # ── Takeover check ──────────────────────────────────────
    if is_thread_takeover_enabled(clinic_id, thread["id"]):
        logger.info("Takeover active for thread=%s, skipping AI", thread["id"])
        return JSONResponse({"status": "takeover_enabled"}, status_code=200)

    # ── Emergency pre-check (fast regex) ────────────────────
    emergency_agent = EmergencyAgent()
    if emergency_agent.quick_check(text):
        logger.warning("Emergency keyword detected from %s", sender_phone)

    # ── Build context ───────────────────────────────────────
    context_msgs = get_last_messages(clinic_id, patient["id"], limit=5)
    history_text = "\n".join(f"{m['direction']}: {m['content']}" for m in context_msgs)

    kb_entries = get_kb_entries(clinic_id)
    kb_text = render_kb(kb_entries)

    # Generate available slots
    settings = get_clinic_settings(clinic_id) or {}
    slots_text = "(No slots checked.)"
    try:
        from db.queries import list_appointments
        booked = list_appointments(clinic_id, status="CONFIRMED", limit=200)
        booked_times = [a["start_time"] for a in booked if a.get("start_time")]
        available = generate_available_slots(settings, booked_times)
        slots_text = format_slots_text(available)
    except Exception as exc:
        logger.warning("Slot generation failed: %s", exc)

    context = {
        "clinic": clinic,
        "patient": {
            "id": str(patient["id"]),
            "name": patient.get("name") or "Patient",
            "phone": sender_phone,
        },
        "thread": thread,
        "history_text": history_text,
        "kb_text": kb_text,
        "slots_text": slots_text,
        "working_hours": f"{settings.get('start_hour', 10)} AM – {settings.get('end_hour', 18)} PM",
        "slot_duration_minutes": settings.get("slot_duration_minutes", 30),
    }

    # ── Run orchestrator pipeline ───────────────────────────
    incoming = IncomingMessage(
        clinic_id=clinic_id,
        sender_phone=sender_phone,
        text=text,
        channel=ChannelSource.WHATSAPP,
        raw_payload=data,
    )

    orchestrator = _get_orchestrator()
    result = orchestrator.process(incoming, context)

    # ── Send reply ──────────────────────────────────────────
    if result.reply_text:
        try:
            send_whatsapp_msg(sender_phone, result.reply_text)
            log_message(clinic_id, patient["id"], thread["id"], "TEXT", "OUTBOUND", result.reply_text)
        except Exception as exc:
            logger.error("Failed to send WhatsApp reply: %s", exc)

    # ── Handle escalation (doctor alert) ────────────────────
    if result.escalate:
        doctor_alert = result.data.get("doctor_alert", "")
        if doctor_alert and clinic.get("contact_phone"):
            try:
                send_whatsapp_msg(clinic["contact_phone"], doctor_alert)
                logger.info("Doctor alerted for emergency: clinic=%s", clinic_id)
            except Exception as exc:
                logger.error("Failed to alert doctor: %s", exc)

    return JSONResponse(
        {"status": "success", "action": result.action},
        status_code=200,
    )
