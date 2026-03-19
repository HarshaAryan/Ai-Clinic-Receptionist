import hashlib
import os

import requests
from fastapi import APIRouter, Form
from fastapi.responses import RedirectResponse
from starlette.requests import Request

from db.queries import (
    check_phone_unique,
    get_admin_by_email,
    get_admin_clinic_by_sub,
    get_or_create_admin_clinic,
    save_onboarding_step,
    update_clinic_profile,
)

router = APIRouter()


# ── Helpers ─────────────────────────────────────────────────


def _auth0_base() -> str:
    domain = os.getenv("AUTH0_DOMAIN")
    if not domain:
        raise RuntimeError("AUTH0_DOMAIN not set")
    return f"https://{domain}"


def _auth0_is_configured() -> bool:
    return bool(
        os.getenv("AUTH0_DOMAIN")
        and os.getenv("AUTH0_CLIENT_ID")
        and os.getenv("AUTH0_CLIENT_SECRET")
        and os.getenv("AUTH0_CALLBACK_URL")
    )


def _allow_dev_auth() -> bool:
    return os.getenv("ALLOW_DEV_AUTH", "true").lower() in ("1", "true", "yes", "on")


def _db_is_configured() -> bool:
    url = os.getenv("SUPABASE_DB_URL", "")
    if not url:
        return False
    # Detect placeholder/template values
    if "your-password" in url or "your-project" in url:
        return False
    return True


def _dev_sub_for_email(email: str) -> str:
    digest = hashlib.sha1(email.strip().lower().encode("utf-8")).hexdigest()[:12]
    return f"dev-{digest}"


def _set_session_identity(request: Request, user: dict, clinic_id: str, role: str, onboarding_status: str):
    request.session["user"] = user
    request.session["clinic_id"] = clinic_id
    request.session["role"] = role
    request.session["onboarding_status"] = onboarding_status


def _clear_session(request: Request):
    """Clear auth-related session keys without destroying the whole session."""
    for key in ("user", "clinic_id", "role", "onboarding_status", "auth_mode", "pre_signup"):
        request.session.pop(key, None)


# ── SIGN UP ─────────────────────────────────────────────────


@router.post("/auth/signup/setup")
def signup_setup(
    request: Request,
    full_name: str = Form(default=""),
    email: str = Form(default=""),
    clinic_name: str = Form(default=""),
    specialization: str = Form(default=""),
    contact_phone: str = Form(default=""),
    timezone: str = Form(default="UTC"),
    working_days: str = Form(default="MON,TUE,WED,THU,FRI"),
    start_hour: int = Form(default=10),
    end_hour: int = Form(default=18),
    slot_duration_minutes: int = Form(default=30),
    cancellation_window_hours: int = Form(default=24),
    reminder_hours_before: int = Form(default=24),
    tone: str = Form(default="Professional"),
    language: str = Form(default="English"),
    faq_text: str = Form(default=""),
    escalation_keywords: str = Form(default="emergency,urgent,pain,scream"),
    emergency_message: str = Form(default="If this is an emergency, please call 112/911 immediately."),
    pathway_id: str = Form(default=""),
    voice_id: str = Form(default=""),
    voice_language: str = Form(default="English"),
    voice_gender: str = Form(default="Neutral"),
    voice_tone: str = Form(default="Calm"),
):
    """Handle sign-up form submission. Creates the doctor profile in the DB."""

    pre_signup = {
        "full_name": full_name.strip(),
        "email": email.strip(),
        "clinic_name": clinic_name.strip(),
        "specialization": specialization.strip(),
        "contact_phone": contact_phone.strip(),
        "timezone": timezone.strip() or "UTC",
        "working_days": working_days.strip(),
        "start_hour": start_hour,
        "end_hour": end_hour,
        "slot_duration_minutes": slot_duration_minutes,
        "cancellation_window_hours": cancellation_window_hours,
        "reminder_hours_before": reminder_hours_before,
        "tone": tone.strip() or "Professional",
        "language": language.strip() or "English",
        "faq_text": faq_text,
        "escalation_keywords": escalation_keywords.strip(),
        "emergency_message": emergency_message.strip(),
        "pathway_id": pathway_id.strip(),
        "voice_id": voice_id.strip(),
        "voice_language": voice_language.strip() or "English",
        "voice_gender": voice_gender.strip() or "Neutral",
        "voice_tone": voice_tone.strip() or "Calm",
    }

    email_value = pre_signup["email"] or "doctor@local.dev"
    full_name_value = pre_signup["full_name"] or "Local Doctor"
    phone_value = pre_signup["contact_phone"]

    # ── Auth0 mode: store data in session and redirect to Auth0 ──
    if _auth0_is_configured():
        request.session["pre_signup"] = pre_signup
        return RedirectResponse("/auth/login?mode=signup", status_code=302)

    # ── Dev-auth mode ───────────────────────────────────────
    if not _allow_dev_auth():
        raise RuntimeError("Auth0 is not configured and dev auth is disabled")

    auth_sub = _dev_sub_for_email(email_value)

    # ── Try DB operations (gracefully fall back if DB not available) ──
    clinic_id = None
    onboarding_status = "COMPLETED"
    try:
        if _db_is_configured():
            # Validate phone uniqueness
            if phone_value and not check_phone_unique(phone_value):
                return RedirectResponse("/?error=phone_taken", status_code=302)

            # Check if account already exists
            existing = get_admin_clinic_by_sub(auth_sub)
            if not existing:
                existing = get_admin_by_email(email_value)
            if existing:
                # Account exists — just log them in
                admin = existing["admin"]
                clinic = existing["clinic"]
                onboarding = existing["onboarding"]
                _set_session_identity(
                    request,
                    {"sub": admin.get("auth0_sub", auth_sub), "email": admin.get("email", email_value), "name": admin.get("full_name", full_name_value)},
                    str(clinic["id"]),
                    admin.get("role", "CLINIC_ADMIN"),
                    onboarding.get("status", "IN_PROGRESS"),
                )
                return RedirectResponse("/dashboard", status_code=302)

            # Create the doctor profile
            profile = get_or_create_admin_clinic(auth_sub, email_value, full_name_value)
            clinic_id = str(profile["clinic"]["id"])

            # Save clinic profile
            update_clinic_profile(clinic_id, pre_signup["clinic_name"], pre_signup["specialization"], phone_value)

            # Save all onboarding steps from the signup wizard
            save_onboarding_step(
                clinic_id, 1,
                {
                    "clinic_name": pre_signup["clinic_name"] or f"{full_name_value} Clinic",
                    "timezone": pre_signup["timezone"],
                    "specialization": pre_signup["specialization"],
                    "contact_phone": phone_value,
                },
            )
            save_onboarding_step(
                clinic_id, 2,
                {
                    "working_days": [d.strip().upper() for d in pre_signup["working_days"].split(",") if d.strip()],
                    "start_hour": pre_signup["start_hour"],
                    "end_hour": pre_signup["end_hour"],
                    "slot_duration_minutes": pre_signup["slot_duration_minutes"],
                    "cancellation_window_hours": pre_signup["cancellation_window_hours"],
                    "reminder_hours_before": pre_signup["reminder_hours_before"],
                },
            )
            save_onboarding_step(
                clinic_id, 3,
                {
                    "tone": pre_signup["tone"],
                    "language": pre_signup["language"],
                    "faq": [line.strip() for line in pre_signup["faq_text"].splitlines() if line.strip()],
                    "escalation_keywords": [k.strip().lower() for k in pre_signup["escalation_keywords"].split(",") if k.strip()],
                    "emergency_message": pre_signup["emergency_message"],
                },
            )
            if pre_signup["pathway_id"] and pre_signup["voice_id"]:
                save_onboarding_step(
                    clinic_id, 4,
                    {
                        "pathway_id": pre_signup["pathway_id"],
                        "voice_id": pre_signup["voice_id"],
                        "voice_language": pre_signup["voice_language"],
                        "voice_gender": pre_signup["voice_gender"],
                        "voice_tone": pre_signup["voice_tone"],
                    },
                )
            onboarding_status = "COMPLETED"
    except Exception:
        # DB not reachable — continue in local/demo mode
        clinic_id = clinic_id or "demo-local-clinic"
        onboarding_status = "COMPLETED"

    # ── Auto-login and redirect to dashboard ────────────────
    _set_session_identity(
        request,
        {"sub": auth_sub, "email": email_value, "name": full_name_value},
        clinic_id or "demo-local-clinic",
        "CLINIC_ADMIN",
        onboarding_status,
    )
    return RedirectResponse("/dashboard", status_code=302)


# ── SIGN IN ─────────────────────────────────────────────────


@router.post("/auth/signin")
def signin(request: Request, email: str = Form(default="")):
    """
    Handle sign-in form submission. Only requires email.
    Looks up the doctor by email and authenticates them.
    """
    email_value = email.strip()
    if not email_value:
        return RedirectResponse("/?error=email_required", status_code=302)

    # ── Auth0 mode ──────────────────────────────────────────
    if _auth0_is_configured():
        request.session["auth_mode"] = "signin"
        request.session["signin_email"] = email_value
        return RedirectResponse("/auth/login?mode=signin", status_code=302)

    # ── Dev-auth mode ───────────────────────────────────────
    if not _allow_dev_auth():
        raise RuntimeError("Auth0 is not configured and dev auth is disabled")

    auth_sub = _dev_sub_for_email(email_value)

    # ── Try DB lookup (fall back to demo mode on failure) ──
    try:
        if not _db_is_configured():
            raise RuntimeError("DB not configured")

        # Look up by auth sub (dev sub derived from email)
        existing = get_admin_clinic_by_sub(auth_sub)
        if not existing:
            # Also try direct email lookup
            existing = get_admin_by_email(email_value)

        if not existing:
            return RedirectResponse("/?error=account_not_found", status_code=302)

        # Found the doctor — set session and redirect
        admin = existing["admin"]
        clinic = existing["clinic"]
        onboarding = existing["onboarding"]

        _set_session_identity(
            request,
            {"sub": admin.get("auth0_sub", auth_sub), "email": admin.get("email", email_value), "name": admin.get("full_name", "Doctor")},
            str(clinic["id"]),
            admin.get("role", "CLINIC_ADMIN"),
            onboarding.get("status", "IN_PROGRESS"),
        )

        if onboarding.get("status") == "COMPLETED":
            return RedirectResponse("/dashboard", status_code=302)
        return RedirectResponse("/setup/step/1", status_code=302)

    except Exception:
        # DB unreachable — demo mode, log in with session-only data
        _set_session_identity(
            request,
            {"sub": auth_sub, "email": email_value, "name": email_value.split("@")[0].title()},
            "demo-local-clinic",
            "CLINIC_ADMIN",
            "COMPLETED",
        )
        return RedirectResponse("/dashboard", status_code=302)


# ── AUTH0 LOGIN REDIRECT ────────────────────────────────────


@router.get("/auth/login")
def login(request: Request, mode: str = "signin"):
    """
    Redirect to Auth0 for authentication.
    In dev-auth mode, this handles the redirect logic directly.
    """
    mode = "signup" if mode == "signup" else "signin"
    request.session["auth_mode"] = mode

    if not _auth0_is_configured():
        # This route shouldn't normally be hit directly in dev mode
        # (signin/signup forms post to /auth/signin and /auth/signup/setup)
        # but handle gracefully for backwards compatibility
        if not _allow_dev_auth():
            raise RuntimeError("Auth0 is not configured and dev auth is disabled")
        return RedirectResponse("/", status_code=302)

    # ── Auth0 redirect ──────────────────────────────────────
    client_id = os.getenv("AUTH0_CLIENT_ID")
    callback = os.getenv("AUTH0_CALLBACK_URL")
    audience = os.getenv("AUTH0_AUDIENCE", "")
    if not client_id or not callback:
        raise RuntimeError("AUTH0_CLIENT_ID or AUTH0_CALLBACK_URL not set")

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": callback,
        "scope": "openid profile email",
        "prompt": "login",
        "screen_hint": "signup" if mode == "signup" else "signin",
    }
    if request.query_params.get("provider") == "google":
        params["connection"] = "google-oauth2"
    if audience:
        params["audience"] = audience

    query = "&".join(f"{k}={requests.utils.quote(str(v))}" for k, v in params.items())
    return RedirectResponse(f"{_auth0_base()}/authorize?{query}")


# ── AUTH0 CALLBACK ──────────────────────────────────────────


@router.get("/auth/callback")
def callback(request: Request, code: str):
    if not _auth0_is_configured():
        return RedirectResponse("/", status_code=302)

    auth_mode = request.session.get("auth_mode", "signin")

    client_id = os.getenv("AUTH0_CLIENT_ID")
    client_secret = os.getenv("AUTH0_CLIENT_SECRET")
    callback_url = os.getenv("AUTH0_CALLBACK_URL")
    if not client_id or not client_secret or not callback_url:
        raise RuntimeError("Auth0 env vars missing")

    token_url = f"{_auth0_base()}/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "code": code,
        "redirect_uri": callback_url,
    }
    token_resp = requests.post(token_url, json=payload, timeout=10)
    token_resp.raise_for_status()
    tokens = token_resp.json()

    userinfo_url = f"{_auth0_base()}/userinfo"
    userinfo = requests.get(
        userinfo_url,
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        timeout=10,
    ).json()

    auth0_sub = userinfo.get("sub")
    if not auth0_sub:
        raise RuntimeError("Auth0 user sub missing")

    existing = get_admin_clinic_by_sub(auth0_sub)

    if auth_mode == "signin":
        if not existing:
            return RedirectResponse("/?error=account_not_found", status_code=302)
        profile = existing
    else:
        # Signup mode
        if existing:
            return RedirectResponse("/?error=account_exists", status_code=302)
        profile = get_or_create_admin_clinic(auth0_sub, userinfo.get("email"), userinfo.get("name"))

    clinic_id = str(profile["clinic"]["id"])

    # Apply pre_signup data if available (from signup wizard)
    pre = request.session.get("pre_signup") or {}
    if pre and auth_mode == "signup":
        phone_value = pre.get("contact_phone", "").strip()
        if phone_value and not check_phone_unique(phone_value, exclude_clinic_id=clinic_id):
            request.session.clear()
            return RedirectResponse("/?error=phone_taken", status_code=302)
        update_clinic_profile(clinic_id, pre.get("clinic_name"), pre.get("specialization"), phone_value or None)

    if auth_mode == "signup":
        # After signup via Auth0, redirect to home with success message
        request.session.clear()
        return RedirectResponse("/?signup=success", status_code=302)

    # Sign-in: set session and go to dashboard
    request.session.pop("pre_signup", None)
    request.session["user"] = userinfo
    request.session["tokens"] = tokens
    request.session["clinic_id"] = clinic_id
    request.session["role"] = profile["admin"].get("role", "CLINIC_ADMIN")
    request.session["onboarding_status"] = profile["onboarding"].get("status", "IN_PROGRESS")

    if profile["onboarding"].get("status") == "COMPLETED":
        return RedirectResponse("/dashboard", status_code=302)
    return RedirectResponse("/setup/step/1", status_code=302)


# ── LOGOUT ──────────────────────────────────────────────────


@router.get("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/")
