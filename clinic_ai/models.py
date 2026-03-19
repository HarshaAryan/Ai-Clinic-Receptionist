"""
ClinicOS — Domain models (Pydantic schemas).
These are used across routers, agents, and services for request/response validation.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ── Enums ───────────────────────────────────────────────────


class AppointmentStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class MessageDirection(str, Enum):
    INBOUND = "INBOUND"
    OUTBOUND = "OUTBOUND"


class MessageType(str, Enum):
    TEXT = "TEXT"
    VOICE = "VOICE"


class ChannelSource(str, Enum):
    WHATSAPP = "WHATSAPP"
    INSTAGRAM = "INSTAGRAM"
    TWITTER = "TWITTER"
    CALL = "CALL"
    EMAIL = "EMAIL"
    WEB = "WEB"


class IntentType(str, Enum):
    APPOINTMENT_BOOK = "APPOINTMENT_BOOK"
    APPOINTMENT_RESCHEDULE = "APPOINTMENT_RESCHEDULE"
    APPOINTMENT_CANCEL = "APPOINTMENT_CANCEL"
    EMERGENCY = "EMERGENCY"
    GENERAL_QUERY = "GENERAL_QUERY"
    SOCIAL_REPLY = "SOCIAL_REPLY"
    FOLLOWUP = "FOLLOWUP"
    UNKNOWN = "UNKNOWN"


class UrgencyLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# ── Clinic ──────────────────────────────────────────────────


class ClinicProfile(BaseModel):
    id: str
    name: str
    specialization: Optional[str] = None
    contact_phone: Optional[str] = None
    timezone: str = "UTC"
    whatsapp_phone_id: Optional[str] = None


class ClinicSettings(BaseModel):
    clinic_id: str
    working_days: List[str] = ["MON", "TUE", "WED", "THU", "FRI"]
    start_hour: int = 10
    end_hour: int = 18
    slot_duration_minutes: int = 30
    cancellation_window_hours: int = 24
    reminder_hours_before: int = 24
    tone: Optional[str] = "Professional"
    language: Optional[str] = "English"
    faq: Optional[List[Any]] = None
    escalation_keywords: Optional[List[str]] = None
    emergency_message: Optional[str] = None


# ── Patient ─────────────────────────────────────────────────


class PatientBase(BaseModel):
    name: Optional[str] = None
    phone: str
    email: Optional[str] = None


class Patient(PatientBase):
    id: str
    clinic_id: str
    tags: List[str] = []
    created_at: Optional[datetime] = None


# ── Appointment ─────────────────────────────────────────────


class AppointmentCreate(BaseModel):
    patient_name: Optional[str] = None
    patient_phone: str
    start_time: datetime
    status: AppointmentStatus = AppointmentStatus.PENDING


class AppointmentPatch(BaseModel):
    status: Optional[AppointmentStatus] = None
    start_time: Optional[datetime] = None
    notes: Optional[str] = None


class Appointment(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    start_time: datetime
    status: AppointmentStatus = AppointmentStatus.PENDING
    calendar_event_id: Optional[str] = None
    source: str = "AI"
    notes: Optional[str] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None


# ── Conversation ────────────────────────────────────────────


class ConversationThread(BaseModel):
    id: str
    clinic_id: str
    patient_id: str
    source: ChannelSource = ChannelSource.WHATSAPP
    takeover_enabled: bool = False
    last_message_at: Optional[datetime] = None
    patient_name: Optional[str] = None
    patient_phone: Optional[str] = None
    last_message: Optional[str] = None


class ConversationMessage(BaseModel):
    id: Optional[str] = None
    clinic_id: str
    patient_id: str
    thread_id: Optional[str] = None
    message_type: MessageType = MessageType.TEXT
    direction: MessageDirection
    content: str
    timestamp: Optional[datetime] = None


class TakeoverPayload(BaseModel):
    takeover_enabled: bool


# ── AI / Agent ──────────────────────────────────────────────


class IntentClassification(BaseModel):
    """Returned by the Master Orchestrator."""
    intent: IntentType
    confidence: float = Field(ge=0, le=1)
    language: str = "english"


class EmergencyAssessment(BaseModel):
    """Returned by the Emergency Agent."""
    is_emergency: bool
    urgency_level: UrgencyLevel = UrgencyLevel.LOW
    emergency_type: str = "none"
    suggested_action: str = "normal_flow"
    patient_message: str = ""


class ReceptionReply(BaseModel):
    """Returned by the Reception Agent."""
    reply: str
    action: str = "none"
    appointment_details: Optional[Dict[str, Any]] = None


class ReminderPayload(BaseModel):
    """Details for a reminder to send."""
    appointment_id: str
    patient_id: str
    patient_phone: str
    patient_name: Optional[str] = None
    appointment_time: datetime
    clinic_name: str
    hours_before: int
    message: str = ""


# ── Metrics ─────────────────────────────────────────────────


class DashboardMetrics(BaseModel):
    appointments: int = 0
    messages: int = 0
    patients: int = 0


# ── Incoming message envelope ───────────────────────────────


class IncomingMessage(BaseModel):
    """Normalized message from any channel."""
    clinic_id: str
    sender_phone: str
    text: str
    channel: ChannelSource = ChannelSource.WHATSAPP
    raw_payload: Optional[Dict[str, Any]] = None
