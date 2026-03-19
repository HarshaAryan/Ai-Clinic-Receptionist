from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel

from db.queries import (
    create_appointment,
    find_or_create_patient,
    get_patient,
    get_thread_messages,
    list_appointments,
    list_patients,
    list_threads,
    patch_appointment,
    set_thread_takeover,
)
from services.auth import get_current_clinic_id

router = APIRouter(prefix="/api")


class TakeoverPayload(BaseModel):
    takeover_enabled: bool


class AppointmentCreatePayload(BaseModel):
    patient_name: Optional[str] = None
    patient_phone: str
    start_time: datetime
    status: str = "PENDING"


class AppointmentPatchPayload(BaseModel):
    status: Optional[str] = None
    start_time: Optional[datetime] = None
    notes: Optional[str] = None


@router.get("/inbox/threads")
def api_threads(request: Request):
    clinic_id = get_current_clinic_id(request)
    return {"items": list_threads(clinic_id)}


@router.get("/inbox/threads/{thread_id}")
def api_thread_messages(request: Request, thread_id: str):
    clinic_id = get_current_clinic_id(request)
    return {"items": get_thread_messages(clinic_id, thread_id)}


@router.post("/inbox/threads/{thread_id}/takeover")
def api_toggle_takeover(request: Request, thread_id: str, payload: TakeoverPayload):
    clinic_id = get_current_clinic_id(request)
    row = set_thread_takeover(clinic_id, thread_id, payload.takeover_enabled)
    if not row:
        raise HTTPException(status_code=404, detail="Thread not found")
    return {"item": row}


@router.get("/appointments")
def api_appointments(request: Request, status: str = ""):
    clinic_id = get_current_clinic_id(request)
    return {"items": list_appointments(clinic_id, status=status or None)}


@router.post("/appointments")
def api_create_appointment(request: Request, payload: AppointmentCreatePayload):
    clinic_id = get_current_clinic_id(request)
    patient = find_or_create_patient(clinic_id, payload.patient_phone, payload.patient_name)
    item = create_appointment(clinic_id, patient["id"], payload.start_time, payload.status)
    return {"item": item}


@router.patch("/appointments/{appointment_id}")
def api_patch_appointment(request: Request, appointment_id: str, payload: AppointmentPatchPayload):
    clinic_id = get_current_clinic_id(request)
    item = patch_appointment(clinic_id, appointment_id, payload.model_dump(exclude_none=True))
    if not item:
        raise HTTPException(status_code=404, detail="Appointment not found or no fields provided")
    return {"item": item}


@router.get("/patients")
def api_patients(request: Request):
    clinic_id = get_current_clinic_id(request)
    return {"items": list_patients(clinic_id)}


@router.get("/patients/{patient_id}")
def api_patient(request: Request, patient_id: str):
    clinic_id = get_current_clinic_id(request)
    item = get_patient(clinic_id, patient_id)
    if not item:
        raise HTTPException(status_code=404, detail="Patient not found")
    return {"item": item}
