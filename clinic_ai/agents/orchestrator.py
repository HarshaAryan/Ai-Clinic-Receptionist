"""
Master Orchestrator — classifies intent and routes to the correct agent.
Maps to the Master Orchestrator in the ClinicOS masterplan.
"""

from __future__ import annotations

import json
from typing import Any, Dict

from agents.base_agent import AgentResult, BaseAgent
from models import IncomingMessage, IntentClassification, IntentType
from services.gemini import classify_intent
from services.logger import logger


class Orchestrator:
    """
    Entry point for every inbound message.
    1. Classify intent via Gemini.
    2. Route to the right agent.
    3. Return the agent's result.
    """

    def __init__(self) -> None:
        self._agents: Dict[IntentType, BaseAgent] = {}

    # ── Registration ────────────────────────────────────────

    def register(self, intent: IntentType, agent: BaseAgent) -> None:
        self._agents[intent] = agent
        logger.info("Agent registered: %s → %s", intent.value, agent.name)

    # ── Main pipeline ───────────────────────────────────────

    def process(self, message: IncomingMessage, context: Dict[str, Any]) -> AgentResult:
        """Run the full classify → route → handle pipeline."""
        clinic_name = context.get("clinic", {}).get("name", "Clinic")

        # 1 — Classify intent
        classification = self._classify(message, clinic_name)
        context["classification"] = classification
        logger.info(
            "Intent: %s (%.0f%%) for clinic=%s sender=%s",
            classification.intent.value,
            classification.confidence * 100,
            message.clinic_id,
            message.sender_phone,
        )

        # 2 — Route
        agent = self._agents.get(classification.intent)
        if not agent:
            # Fallback to general query handler or return a default
            agent = self._agents.get(IntentType.GENERAL_QUERY)
        if not agent:
            logger.warning("No agent registered for intent %s", classification.intent.value)
            return AgentResult(
                reply_text="I'm sorry, I couldn't understand your request. Could you rephrase?",
                action="none",
            )

        # 3 — Handle
        logger.info("Routing to %s", agent.name)
        try:
            result = agent.handle(message, context)
        except Exception as exc:
            logger.exception("Agent %s failed: %s", agent.name, exc)
            result = AgentResult(
                reply_text="Sorry, something went wrong. Please try again in a moment.",
                error=str(exc),
            )
        return result

    # ── Internal ────────────────────────────────────────────

    @staticmethod
    def _classify(message: IncomingMessage, clinic_name: str) -> IntentClassification:
        """Ask Gemini to classify the intent."""
        try:
            raw = classify_intent(
                message_text=message.text,
                channel=message.channel.value,
                sender_phone=message.sender_phone,
                clinic_name=clinic_name,
            )
            # Parse the JSON from Gemini response
            # Strip markdown code fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            data = json.loads(cleaned)
            return IntentClassification(
                intent=IntentType(data.get("intent", "UNKNOWN")),
                confidence=float(data.get("confidence", 0.5)),
                language=data.get("language", "english"),
            )
        except Exception as exc:
            logger.warning("Intent classification failed, defaulting to UNKNOWN: %s", exc)
            return IntentClassification(
                intent=IntentType.UNKNOWN,
                confidence=0.0,
                language="english",
            )
