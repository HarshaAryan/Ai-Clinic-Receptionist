import os

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db.queries import get_onboarding_state, save_onboarding_step
from services.auth import get_current_user, get_current_clinic_id

router = APIRouter()
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(_BASE, "templates"))


@router.get("/setup/step/{step}", response_class=HTMLResponse)
def setup_step(request: Request, step: int):
    user = get_current_user(request)
    try:
        clinic_id = get_current_clinic_id(request)
        onboarding = get_onboarding_state(clinic_id)
        if onboarding.get("status") == "COMPLETED":
            return RedirectResponse("/dashboard", status_code=302)
    except Exception:
        onboarding = {"status": request.session.get("onboarding_status", "IN_PROGRESS")}
        if onboarding.get("status") == "COMPLETED":
            return RedirectResponse("/dashboard", status_code=302)

    step = max(1, min(4, int(step)))
    return templates.TemplateResponse(
        "setup_wizard.html",
        {
            "request": request,
            "user": user,
            "step": step,
            "error": "",
        },
    )


@router.post("/setup/step/{step}")
def save_step(
    request: Request,
    step: int,
    clinic_name: str = Form(default=""),
    timezone: str = Form(default="UTC"),
    specialization: str = Form(default=""),
    contact_phone: str = Form(default=""),
    working_days: str = Form(default="MON,TUE,WED,THU,FRI"),
    start_hour: int = Form(default=10),
    end_hour: int = Form(default=18),
    slot_duration_minutes: int = Form(default=30),
    cancellation_window_hours: int = Form(default=24),
    reminder_hours_before: int = Form(default=24),
    tone: str = Form(default="Professional"),
    language: str = Form(default="English"),
    faq_text: str = Form(default=""),
    escalation_keywords: str = Form(default="emergency,urgent,pain"),
    emergency_message: str = Form(default="If this is an emergency, please call 112/911 immediately."),
    pathway_id: str = Form(default=""),
    voice_id: str = Form(default=""),
    voice_language: str = Form(default="English"),
    voice_gender: str = Form(default="Neutral"),
    voice_tone: str = Form(default="Calm"),
):
    step = max(1, min(4, int(step)))

    payload = {}
    if step == 1:
        if not clinic_name.strip():
            return templates.TemplateResponse(
                "setup_wizard.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "step": 1,
                    "error": "Clinic name is required.",
                },
                status_code=422,
            )
        payload = {
            "clinic_name": clinic_name.strip(),
            "timezone": timezone,
            "specialization": specialization,
            "contact_phone": contact_phone,
        }
    elif step == 2:
        payload = {
            "working_days": [d.strip().upper() for d in working_days.split(",") if d.strip()],
            "start_hour": start_hour,
            "end_hour": end_hour,
            "slot_duration_minutes": slot_duration_minutes,
            "cancellation_window_hours": cancellation_window_hours,
            "reminder_hours_before": reminder_hours_before,
        }
    elif step == 3:
        faq = [line.strip() for line in faq_text.splitlines() if line.strip()]
        payload = {
            "tone": tone,
            "language": language,
            "faq": faq,
            "escalation_keywords": [k.strip().lower() for k in escalation_keywords.split(",") if k.strip()],
            "emergency_message": emergency_message,
        }
    elif step == 4:
        if not pathway_id.strip() or not voice_id.strip():
            return templates.TemplateResponse(
                "setup_wizard.html",
                {
                    "request": request,
                    "user": get_current_user(request),
                    "step": 4,
                    "error": "Both pathway ID and voice ID are required for Bland setup.",
                },
                status_code=422,
            )
        payload = {
            "pathway_id": pathway_id.strip(),
            "voice_id": voice_id.strip(),
            "voice_language": voice_language,
            "voice_gender": voice_gender,
            "voice_tone": voice_tone,
        }

    try:
        clinic_id = get_current_clinic_id(request)
        state = save_onboarding_step(clinic_id, step, payload)
        request.session["onboarding_status"] = state.get("status")
    except Exception:
        if step >= 4:
            request.session["onboarding_status"] = "COMPLETED"
        else:
            request.session["onboarding_status"] = "IN_PROGRESS"
        state = {"status": request.session["onboarding_status"]}

    if step >= 4 or state.get("status") == "COMPLETED":
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse(f"/setup/step/{step + 1}", status_code=302)
