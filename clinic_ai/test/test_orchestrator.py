"""Tests for the Orchestrator intent routing."""

import json
from unittest.mock import patch

from agents.base_agent import AgentResult, BaseAgent
from agents.orchestrator import Orchestrator
from models import ChannelSource, IncomingMessage, IntentType


class _StubAgent(BaseAgent):
    name = "StubAgent"

    def handle(self, message, context):
        return AgentResult(reply_text=f"Handled by {self.name}", action="test")


def _msg(text: str) -> IncomingMessage:
    return IncomingMessage(
        clinic_id="test-clinic",
        sender_phone="919999999999",
        text=text,
        channel=ChannelSource.WHATSAPP,
    )


class TestOrchestrator:
    @patch("agents.orchestrator.classify_intent")
    def test_routes_to_registered_agent(self, mock_classify):
        mock_classify.return_value = json.dumps({
            "intent": "GENERAL_QUERY",
            "confidence": 0.9,
            "language": "english",
        })
        orch = Orchestrator()
        agent = _StubAgent()
        orch.register(IntentType.GENERAL_QUERY, agent)

        result = orch.process(_msg("what are your fees?"), {"clinic": {"name": "Test"}})
        assert result.reply_text == "Handled by StubAgent"
        assert result.action == "test"

    @patch("agents.orchestrator.classify_intent")
    def test_fallback_when_no_agent(self, mock_classify):
        mock_classify.return_value = json.dumps({
            "intent": "SOCIAL_REPLY",
            "confidence": 0.8,
            "language": "english",
        })
        orch = Orchestrator()
        # No agents registered at all
        result = orch.process(_msg("nice post!"), {"clinic": {"name": "Test"}})
        assert "couldn't understand" in result.reply_text.lower() or "rephrase" in result.reply_text.lower()

    @patch("agents.orchestrator.classify_intent")
    def test_handles_malformed_json(self, mock_classify):
        mock_classify.return_value = "not valid json at all"

        orch = Orchestrator()
        agent = _StubAgent()
        orch.register(IntentType.UNKNOWN, agent)

        result = orch.process(_msg("hello"), {"clinic": {"name": "Test"}})
        # Should fall back to UNKNOWN intent → StubAgent
        assert result.reply_text == "Handled by StubAgent"
