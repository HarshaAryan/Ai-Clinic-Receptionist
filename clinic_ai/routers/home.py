import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter()
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(_BASE, "templates"))


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "user": request.session.get("user"),
            "signup_success": request.query_params.get("signup") == "success",
            "calendar_connected": request.query_params.get("calendar") == "connected",
            "error": request.query_params.get("error", ""),
            "onboarding_status": request.session.get("onboarding_status", "IN_PROGRESS"),
        },
    )
