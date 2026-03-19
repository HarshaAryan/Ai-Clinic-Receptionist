"""
Emergency Agent (AlertBot) — detects emergencies in any channel,
alerts the doctor immediately, and sends the patient reassurance.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict

from agents.base_agent import AgentResult, BaseAgent
from models import EmergencyAssessment, IncomingMessage, UrgencyLevel
from services.gemini import detect_emergency
from services.logger import logger


# Fast keyword pre-filter so we don't call Gemini on every message
_EMERGENCY_KEYWORDS = re.compile(
    r"\b("
    r"chest\s*pain|heart\s*attack|difficulty\s*breathing|breathless|"
    r"unconscious|accident|heavy\s*bleeding|bleeding\s*a\s*lot|"
    r"stroke|seizure|severe\s*pain|faint|passed\s*out|"
    r"ambulance|emergency|urgent|can't\s*breathe|"
    r"critical|choking|poisoning|burn|fracture|"
    # Hindi/Hinglish
    r"dard|bahut\s*dard|saans\s*nahi|behosh|khoon|"
    r"emergency|urgent|doctor\s*immediately|jaldi"
    r")\b",
    re.IGNORECASE,
)


class EmergencyAgent(BaseAgent):
    """
    Scans every message for emergency signals.
    - Fast regex pre-check
    - If triggered → Gemini deep assessment
    - If emergency confirmed → alert doctor, reassure patient
    """

    name = "EmergencyAgent"

    def handle(self, message: IncomingMessage, context: Dict[str, Any]) -> AgentResult:
        assessment = self.assess(message, context)

        if not assessment.is_emergency:
            return AgentResult(
                reply_text="",
                action="normal_flow",
                data={"assessment": assessment.model_dump()},
            )

        # Emergency confirmed
        logger.critical(
            "🚨 EMERGENCY detected  clinic=%s phone=%s type=%s urgency=%s",
            message.clinic_id,
            message.sender_phone,
            assessment.emergency_type,
            assessment.urgency_level.value,
        )

        # Build patient reassurance message
        patient_msg = assessment.patient_message or (
            "We have flagged your message as urgent. "
            "If this is a medical emergency, please call 112 or go to the nearest hospital immediately. "
            "Our doctor has been notified."
        )

        return AgentResult(
            reply_text=patient_msg,
            action="alert_doctor",
            data={
                "assessment": assessment.model_dump(),
                "doctor_alert": self._build_doctor_alert(message, assessment, context),
            },
            escalate=True,
        )

    # ── Public helper: can be called on ANY message ─────────

    def quick_check(self, text: str) -> bool:
        """Fast regex check — returns True if text may be an emergency."""
        return bool(_EMERGENCY_KEYWORDS.search(text))

    def assess(self, message: IncomingMessage, context: Dict[str, Any]) -> EmergencyAssessment:
        """Full assessment via Gemini."""
        try:
            raw = detect_emergency(
                message_text=message.text,
                channel=message.channel.value,
            )
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]

            data = json.loads(cleaned.strip())
            return EmergencyAssessment(
                is_emergency=data.get("is_emergency", False),
                urgency_level=UrgencyLevel(data.get("urgency_level", "low")),
                emergency_type=data.get("emergency_type", "none"),
                suggested_action=data.get("suggested_action", "normal_flow"),
                patient_message=data.get("patient_message", ""),
            )
        except Exception as exc:
            logger.warning("Emergency assessment parse failed: %s", exc)
            # Conservative: if regex matched but Gemini failed, treat as potential emergency
            is_kw = self.quick_check(message.text)
            return EmergencyAssessment(
                is_emergency=is_kw,
                urgency_level=UrgencyLevel.MEDIUM if is_kw else UrgencyLevel.LOW,
                emergency_type="unknown" if is_kw else "none",
                suggested_action="call_doctor_immediately" if is_kw else "normal_flow",
                patient_message="If this is an emergency, please call 112 immediately.",
            )

    # ── Internal ────────────────────────────────────────────

    @staticmethod
    def _build_doctor_alert(
        message: IncomingMessage,
        assessment: EmergencyAssessment,
        context: Dict[str, Any],
    ) -> str:
        patient_name = context.get("patient", {}).get("name", "Unknown")
        return (
            f"🚨 EMERGENCY ALERT\n"
            f"Patient: {patient_name} ({message.sender_phone})\n"
            f"Channel: {message.channel.value}\n"
            f"Type: {assessment.emergency_type}\n"
            f"Urgency: {assessment.urgency_level.value}\n"
            f"Message: {message.text[:200]}"
        )
