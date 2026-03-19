import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from db.queries import (
    get_clinic_google_tokens,
    get_metrics,
    list_appointments,
    list_patients,
    list_threads,
    get_thread_messages,
    get_onboarding_state,
)
from services.auth import get_current_user, get_current_clinic_id

router = APIRouter()
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(_BASE, "templates"))

VALID_TABS = {"overview", "inbox", "appointments", "patients", "emergency", "settings"}


def _load_emergency_alerts(clinic_id: str) -> list:
    """Try to load emergency alerts from DB; return empty list on failure."""
    try:
        from db.session import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT id, clinic_id, patient_phone, message_text, resolved, created_at "
            "FROM emergency_alerts WHERE clinic_id = %s ORDER BY created_at DESC LIMIT 50",
            (clinic_id,),
        )
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        return rows
    except Exception:
        return []


def _load_clinic_profile(clinic_id: str) -> dict:
    """Try to load clinic profile + settings; return sensible defaults on failure."""
    try:
        from db.session import get_conn

        conn = get_conn()
        cur = conn.cursor()
        cur.execute(
            "SELECT name, specialization, contact_phone, timezone FROM clinics WHERE id = %s",
            (clinic_id,),
        )
        row = cur.fetchone()
        profile = {}
        if row:
            profile = {
                "name": row[0],
                "specialization": row[1],
                "contact_phone": row[2],
                "timezone": row[3],
            }

        cur.execute(
            "SELECT settings FROM clinic_settings WHERE clinic_id = %s", (clinic_id,)
        )
        srow = cur.fetchone()
        if srow and srow[0]:
            s = srow[0] if isinstance(srow[0], dict) else {}
            profile.update(
                {
                    "working_days": s.get("working_days", "MON-FRI"),
                    "start_hour": s.get("start_hour", 10),
                    "end_hour": s.get("end_hour", 18),
                    "slot_duration": s.get("slot_duration_minutes", 30),
                    "tone": s.get("tone", "Professional"),
                    "language": s.get("language", "English"),
                }
            )
        cur.close()
        return profile
    except Exception:
        return {
            "name": "My Clinic",
            "specialization": "—",
            "contact_phone": "—",
            "timezone": "Asia/Kolkata",
            "working_days": "MON-FRI",
            "start_hour": 10,
            "end_hour": 18,
            "slot_duration": 30,
            "tone": "Professional",
            "language": "English",
        }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, tab: str = "overview", thread_id: str = ""):
    # Validate tab
    if tab not in VALID_TABS:
        tab = "overview"

    user = get_current_user(request)
    data_warning = ""
    clinic_id = None

    # ── Core data (always loaded) ────────────────────────
    try:
        clinic_id = get_current_clinic_id(request)
        onboarding = get_onboarding_state(clinic_id)
        session_status = request.session.get("onboarding_status", "")
        if onboarding.get("status") != "COMPLETED" and session_status != "COMPLETED":
            return RedirectResponse("/setup/step/1", status_code=302)

        metrics = get_metrics(clinic_id)
        threads = list_threads(clinic_id, limit=30)
        for thread in threads:
            thread["id"] = str(thread["id"])
        appointments = list_appointments(clinic_id, limit=50)
        patients = list_patients(clinic_id, limit=100)

        selected_thread = thread_id or (threads[0]["id"] if threads else "")
        thread_messages = (
            get_thread_messages(clinic_id, selected_thread, limit=100)
            if selected_thread
            else []
        )
    except Exception:
        metrics = {"appointments": 0, "messages": 0, "patients": 0}
        threads = []
        appointments = []
        patients = []
        selected_thread = ""
        thread_messages = []
        data_warning = "Running in local demo mode. Configure Supabase/Auth0 for live data."

    # ── Tab-specific data ────────────────────────────────
    emergency_alerts = []
    if tab == "emergency" and clinic_id:
        emergency_alerts = _load_emergency_alerts(clinic_id)

    clinic_profile = {}
    if tab == "settings":
        clinic_profile = _load_clinic_profile(clinic_id) if clinic_id else _load_clinic_profile("")

    whatsapp_configured = bool(os.getenv("PHONE_ID") and os.getenv("WHATSAPP_TOKEN"))

    # ── Google Calendar connection status ────────────────
    calendar_connected = False
    if clinic_id:
        try:
            tokens = get_clinic_google_tokens(clinic_id)
            calendar_connected = bool(tokens and tokens.get("access_token"))
        except Exception:
            pass

    return templates.TemplateResponse(
        "dashboard_shell.html",
        {
            "request": request,
            "user": user,
            "tab": tab,
            "data_warning": data_warning,
            "metrics": metrics,
            "threads": threads,
            "appointments": appointments,
            "patients": patients,
            "selected_thread": selected_thread,
            "thread_messages": thread_messages,
            "emergency_alerts": emergency_alerts,
            "clinic_profile": clinic_profile,
            "whatsapp_configured": whatsapp_configured,
            "calendar_connected": calendar_connected,
        },
    )
