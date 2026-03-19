import os

from dotenv import load_dotenv

# Load .env BEFORE any other imports so env vars (SUPABASE_DB_URL etc.)
# are available when modules like db/session.py read them at import time.
load_dotenv()

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from routers.api import router as api_router
from routers.auth import router as auth_router
from routers.calendar import router as calendar_router
from routers.dashboard import router as dashboard_router
from routers.home import router as home_router
from routers.reminders import router as reminders_router
from routers.setup import router as setup_router
from routers.whatsapp import router as whatsapp_router
from services.logger import logger

app = FastAPI(
    title="ClinicOS — AI-Powered Clinic Growth Platform",
    description="Agentic reception, reminders, emergency detection & more for Indian clinics.",
    version="2.0.0",
)

session_secret = os.getenv("SESSION_SECRET", "dev-secret")
app.add_middleware(SessionMiddleware, secret_key=session_secret)

# ── Routers ─────────────────────────────────────────────────
app.include_router(home_router)
app.include_router(auth_router)
app.include_router(setup_router)
app.include_router(dashboard_router)
app.include_router(calendar_router)
app.include_router(api_router)
app.include_router(reminders_router)
app.include_router(whatsapp_router)


# ── Startup ─────────────────────────────────────────────────
@app.on_event("startup")
async def on_startup():
    db_url = os.getenv("SUPABASE_DB_URL", "")
    db_ok = bool(db_url) and "your-password" not in db_url and "your-project" not in db_url
    logger.info("🏥 ClinicOS starting up")
    logger.info(
        "DB configured: %s | Gemini configured: %s | WhatsApp configured: %s",
        db_ok,
        bool(os.getenv("GEMINI_API_KEY")),
        bool(os.getenv("PHONE_ID") and os.getenv("WHATSAPP_TOKEN")),
    )
