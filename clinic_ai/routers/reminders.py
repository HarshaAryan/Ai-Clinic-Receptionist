"""
ClinicOS — Reminder & scheduler endpoints.
Provides a manual trigger endpoint and a cron-compatible endpoint
for sending appointment reminders.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from db.queries import get_clinic_by_id
from services.auth import get_current_clinic_id
from services.logger import logger
from services.reminder import run_reminders_for_clinic

router = APIRouter(prefix="/api")


class ReminderResult(BaseModel):
    appointment_id: str
    patient_phone: str
    hours_before: int
    status: str
    error: str = ""


class ReminderResponse(BaseModel):
    clinic_id: str
    sent: List[ReminderResult]


@router.post("/reminders/send", response_model=ReminderResponse)
def trigger_reminders(request: Request, hours_before: int = 24):
    """
    Manually trigger reminders for the current clinic.
    Can also be called by an external scheduler (APScheduler, cron, n8n).
    """
    clinic_id = get_current_clinic_id(request)
    clinic = get_clinic_by_id(clinic_id)
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")

    results = run_reminders_for_clinic(clinic_id, hours_before=hours_before)
    logger.info("Reminders triggered: clinic=%s results=%d", clinic_id, len(results))

    return ReminderResponse(
        clinic_id=clinic_id,
        sent=[ReminderResult(**r) for r in results],
    )


@router.post("/reminders/cron")
def cron_reminders():
    """
    Cron-compatible endpoint: sends 24h + 2h reminders for ALL clinics.
    Secured by a bearer token or internal-only network in production.
    """
    from db.session import db_cursor

    with db_cursor() as cur:
        cur.execute("SELECT id FROM clinics")
        clinics = cur.fetchall() or []

    total_sent = 0
    for c in clinics:
        cid = str(c["id"])
        # 24-hour reminders
        results_24 = run_reminders_for_clinic(cid, hours_before=24)
        # 2-hour reminders
        results_2 = run_reminders_for_clinic(cid, hours_before=2)
        total_sent += len(results_24) + len(results_2)

    logger.info("Cron reminders: processed %d clinics, sent %d reminders", len(clinics), total_sent)
    return {"clinics_processed": len(clinics), "reminders_sent": total_sent}
