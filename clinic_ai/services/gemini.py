"""
ClinicOS — Gemini AI service.
Provides purpose-specific functions, each with its own tailored prompt
as defined in the ClinicOS masterplan.
"""

from __future__ import annotations

import os
from datetime import datetime

import google.generativeai as genai

from services.logger import logger

_configured = False


def _ensure_configured() -> None:
    global _configured
    if _configured:
        return
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")
    genai.configure(api_key=api_key)
    _configured = True


def _model_name() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-1.5-pro")


def _temperature() -> float:
    return float(os.getenv("GEMINI_TEMPERATURE", "0.2"))


def _call(prompt: str) -> str:
    _ensure_configured()
    model = genai.GenerativeModel(_model_name())
    response = model.generate_content(
        prompt,
        generation_config={"temperature": _temperature()},
    )
    return response.text


# ────────────────────────────────────────────────────────────
# 1. MASTER INTENT CLASSIFIER
# ────────────────────────────────────────────────────────────


def classify_intent(
    message_text: str,
    channel: str = "WHATSAPP",
    sender_phone: str = "",
    clinic_name: str = "Clinic",
) -> str:
    """Classify a patient message into one of the defined intents. Returns raw JSON string."""
    prompt = f"""You are ClinicOS, an AI assistant for a medical clinic in India.

A message has arrived from channel: {channel}
Message: {message_text}
Sender: {sender_phone}
Clinic: {clinic_name}

Classify the intent as ONE of:
- APPOINTMENT_BOOK: wants to book/schedule
- APPOINTMENT_RESCHEDULE: wants to change timing
- APPOINTMENT_CANCEL: wants to cancel
- EMERGENCY: medical emergency, urgent, chest pain, accident, bleeding
- GENERAL_QUERY: asking about services, fees, timing, location
- SOCIAL_REPLY: comment/DM on social media
- FOLLOWUP: post-visit question
- UNKNOWN: cannot determine

Respond ONLY with JSON:
{{"intent": "APPOINTMENT_BOOK", "confidence": 0.95, "language": "hindi/english/hinglish"}}"""

    logger.debug("Classifying intent for: %s", message_text[:80])
    return _call(prompt)


# ────────────────────────────────────────────────────────────
# 2. RECEPTION AGENT REPLY
# ────────────────────────────────────────────────────────────


def reception_reply(
    user_text: str,
    clinic_name: str,
    doctor_name: str = "Doctor",
    specialty: str = "General",
    working_hours: str = "Mon-Fri, 10 AM – 6 PM",
    services_list: str = "General consultation",
    fees: str = "As per consultation",
    kb_text: str = "",
    slots_text: str = "",
    patient_history: str = "",
    classified_intent: str = "GENERAL_QUERY",
) -> str:
    """Generate a reception-style reply for the patient. Returns raw text or JSON string."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    prompt = f"""You are ReceptBot, the AI receptionist for {clinic_name} in India.
Doctor: Dr. {doctor_name} | Specialty: {specialty}
Working hours: {working_hours}
Services: {services_list}
Fees: {fees}
Today: {today}

Patient message: {user_text}
Intent: {classified_intent}
Patient history: {patient_history or '(new patient)'}
Available slots: {slots_text or '(not checked)'}

Knowledge Base:
{kb_text or '(none)'}

Your job:
1. Reply warmly in the same language as patient (Hindi/English/Hinglish)
2. If booking — confirm slot, collect name+age+phone if new patient
3. If query — answer from clinic info above
4. Keep replies SHORT (WhatsApp style, under 100 words)
5. Always end with a helpful next step

Respond with JSON:
{{
  "reply": "message to send patient",
  "action": "book_appointment / send_info / escalate_to_doctor / none",
  "appointment_details": {{}}
}}"""

    return _call(prompt)


# ────────────────────────────────────────────────────────────
# 3. EMERGENCY DETECTION
# ────────────────────────────────────────────────────────────


def detect_emergency(message_text: str, channel: str = "WHATSAPP") -> str:
    """Assess whether a message is an emergency. Returns raw JSON string."""
    prompt = f"""You are AlertBot, emergency detector for a medical clinic.

Analyze this message for emergency signals:
Message: {message_text}
Channel: {channel}

Emergency signals: chest pain, heart attack, difficulty breathing,
unconscious, accident, heavy bleeding, stroke, seizure, severe pain,
"doctor immediately", "emergency", "ambulance", critical

Respond with JSON:
{{
  "is_emergency": true/false,
  "urgency_level": "critical/high/medium/low",
  "emergency_type": "cardiac/respiratory/trauma/other/none",
  "suggested_action": "call_doctor_immediately / send_emergency_info / normal_flow",
  "patient_message": "Reassuring message to send patient in their language"
}}"""

    return _call(prompt)


# ────────────────────────────────────────────────────────────
# 4. REMINDER MESSAGE GENERATION
# ────────────────────────────────────────────────────────────


def generate_reminder_message(
    patient_name: str,
    clinic_name: str,
    appointment_time: str,
    hours_before: int = 24,
) -> str:
    """Generate a friendly appointment reminder message."""
    kind = "follow-up" if hours_before == 0 else f"{hours_before}-hour reminder"
    prompt = f"""You are NudgeBot, the reminder agent for {clinic_name} (India).

Generate a short, friendly WhatsApp {kind} message.
Patient name: {patient_name}
Appointment: {appointment_time}
Clinic: {clinic_name}

Rules:
- Under 60 words
- Warm, professional tone
- If it's a reminder: mention time, ask to arrive 10 min early, say "Reply CANCEL to cancel"
- If it's a follow-up (hours_before=0): thank them for visiting, ask how they're feeling
- Use relevant emojis (1-2 max)
- Write in English (or Hinglish if name suggests Hindi speaker)

Return ONLY the message text, no JSON."""

    return _call(prompt).strip().strip('"')


# ────────────────────────────────────────────────────────────
# 5. LEGACY COMPATIBILITY — simple response (used by old code paths & tests)
# ────────────────────────────────────────────────────────────


def build_system_prompt(clinic_name: str, kb_text: str, slots_text: str) -> str:
    """Legacy prompt builder — kept for backward compatibility."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    return (
        f"You are the receptionist for {clinic_name}. Today is {today}.\n"
        "Rules:\n"
        "1. Be polite and concise.\n"
        "2. Your goal is to book an appointment.\n"
        "3. Available slots (if provided) are in the slots list.\n"
        "4. If they ask for medical advice, say: 'I cannot provide medical advice, please visit the clinic.'\n"
        "5. If they mention emergency symptoms or urgent care, advise calling 112/911.\n"
        "6. Respond in under 50 words.\n\n"
        f"Knowledge Base:\n{kb_text}\n\n"
        f"Available Slots:\n{slots_text}\n"
    )


def get_gemini_response(user_text: str, clinic_name: str, kb_text: str, slots_text: str) -> str:
    """Legacy function — used by existing code paths."""
    _ensure_configured()
    model = genai.GenerativeModel(_model_name())
    system_prompt = build_system_prompt(clinic_name, kb_text, slots_text)
    response = model.generate_content(
        f"{system_prompt}\nUser: {user_text}",
        generation_config={"temperature": _temperature()},
    )
    return response.text
