import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

from services.auth import get_current_clinic_id, get_current_user
from db.queries import store_clinic_google_tokens

router = APIRouter()

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def _flow(state: str = None):
    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")
    redirect_uri = os.getenv("GOOGLE_OAUTH_REDIRECT_URI")
    if not client_id or not client_secret or not redirect_uri:
        raise RuntimeError("Google OAuth env vars missing")

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
        state=state,
    )
    flow.redirect_uri = redirect_uri
    return flow


@router.get("/calendar/connect")
def connect_calendar(request: Request, next: str = "/dashboard"):
    get_current_user(request)
    clinic_id = get_current_clinic_id(request)
    request.session["calendar_next"] = next

    flow = _flow(state=str(clinic_id))
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return RedirectResponse(auth_url)


@router.get("/calendar/callback")
def calendar_callback(request: Request, code: str, state: str):
    flow = _flow(state=state)
    flow.fetch_token(code=code)
    creds = flow.credentials
    token_payload = {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": creds.scopes,
    }
    try:
        store_clinic_google_tokens(state, token_payload)
    except Exception:
        # Keep UX resilient when DB is not configured in local demo mode.
        pass
    next_url = request.session.pop("calendar_next", "/dashboard")
    sep = "&" if "?" in next_url else "?"
    return RedirectResponse(f"{next_url}{sep}calendar=connected")
