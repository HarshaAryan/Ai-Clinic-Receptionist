"""
Base agent interface for ClinicOS.
All agents inherit from this and implement `handle()`.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from models import IncomingMessage


@dataclass
class AgentResult:
    """Standardised output from every agent."""

    reply_text: str = ""
    action: str = "none"  # e.g. book_appointment, send_info, escalate, alert_doctor
    data: Dict[str, Any] = field(default_factory=dict)
    escalate: bool = False
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        return self.error is None


class BaseAgent(ABC):
    """Every agent must implement `handle`."""

    name: str = "BaseAgent"

    @abstractmethod
    def handle(self, message: IncomingMessage, context: Dict[str, Any]) -> AgentResult:
        """
        Process an incoming message and return a result.

        Args:
            message: The normalized incoming message.
            context: Dict with keys like clinic, patient, thread,
                     history, kb_text, slots_text, etc.
        """
        ...
