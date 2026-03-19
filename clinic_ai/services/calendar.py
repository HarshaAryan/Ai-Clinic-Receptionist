import os
from datetime import datetime
from typing import Dict, Any, List

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

GOOGLE_SCOPES = ["https://www.googleapis.com/auth/calendar"]


def build_credentials(token_payload: Dict[str, Any]) -> Credentials:
    return Credentials(
        token=token_payload.get("access_token"),
        refresh_token=token_payload.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=GOOGLE_SCOPES,
    )


def get_calendar_service(token_payload: Dict[str, Any]):
    creds = build_credentials(token_payload)
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


def get_free_busy(token_payload: Dict[str, Any], time_min: datetime, time_max: datetime, calendar_id: str = "primary") -> List[Dict[str, Any]]:
    service = get_calendar_service(token_payload)
    body = {
        "timeMin": time_min.isoformat(),
        "timeMax": time_max.isoformat(),
        "items": [{"id": calendar_id}],
    }
    result = service.freebusy().query(body=body).execute()
    return result.get("calendars", {}).get(calendar_id, {}).get("busy", [])


def create_event(
    token_payload: Dict[str, Any],
    start_time: datetime,
    end_time: datetime,
    summary: str,
    description: str,
    calendar_id: str = "primary",
) -> str:
    service = get_calendar_service(token_payload)
    event = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_time.isoformat()},
        "end": {"dateTime": end_time.isoformat()},
    }
    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    return created.get("id")
