"""Tests for the Emergency Agent — keyword detection and assessment parsing."""

import json
from unittest.mock import patch

from agents.emergency import EmergencyAgent
from models import ChannelSource, IncomingMessage


def _msg(text: str) -> IncomingMessage:
    return IncomingMessage(
        clinic_id="test-clinic",
        sender_phone="919999999999",
        text=text,
        channel=ChannelSource.WHATSAPP,
    )


class TestQuickCheck:
    """Fast regex-based emergency keyword detection."""

    def test_detects_chest_pain(self):
        agent = EmergencyAgent()
        assert agent.quick_check("I am having chest pain") is True

    def test_detects_hindi_keywords(self):
        agent = EmergencyAgent()
        assert agent.quick_check("bahut dard ho raha hai") is True

    def test_detects_bleeding(self):
        agent = EmergencyAgent()
        assert agent.quick_check("heavy bleeding from wound") is True

    def test_ignores_normal_message(self):
        agent = EmergencyAgent()
        assert agent.quick_check("I want to book an appointment tomorrow") is False

    def test_detects_ambulance(self):
        agent = EmergencyAgent()
        assert agent.quick_check("please send ambulance") is True

    def test_detects_unconscious(self):
        agent = EmergencyAgent()
        assert agent.quick_check("my father is unconscious") is True


class TestEmergencyHandle:
    """Full handle() with mocked Gemini."""

    @patch("agents.emergency.detect_emergency")
    def test_emergency_confirmed(self, mock_detect):
        mock_detect.return_value = json.dumps({
            "is_emergency": True,
            "urgency_level": "critical",
            "emergency_type": "cardiac",
            "suggested_action": "call_doctor_immediately",
            "patient_message": "Please call 112 immediately.",
        })
        agent = EmergencyAgent()
        result = agent.handle(_msg("having chest pain"), {"patient": {"name": "Test"}})
        assert result.escalate is True
        assert result.action == "alert_doctor"
        assert "112" in result.reply_text

    @patch("agents.emergency.detect_emergency")
    def test_not_emergency(self, mock_detect):
        mock_detect.return_value = json.dumps({
            "is_emergency": False,
            "urgency_level": "low",
            "emergency_type": "none",
            "suggested_action": "normal_flow",
            "patient_message": "",
        })
        agent = EmergencyAgent()
        result = agent.handle(_msg("what are your fees?"), {"patient": {"name": "Test"}})
        assert result.escalate is False
        assert result.action == "normal_flow"
