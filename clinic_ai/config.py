"""
Centralized configuration for ClinicOS platform.
All environment variables are loaded once and validated here.
"""

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class DatabaseConfig:
    url: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.url)


@dataclass(frozen=True)
class Auth0Config:
    domain: str = ""
    client_id: str = ""
    client_secret: str = ""
    callback_url: str = ""
    audience: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.domain and self.client_id and self.client_secret and self.callback_url)


@dataclass(frozen=True)
class GoogleOAuthConfig:
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret and self.redirect_uri)


@dataclass(frozen=True)
class GeminiConfig:
    api_key: str = ""
    model_name: str = "gemini-1.5-pro"
    temperature: float = 0.2

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


@dataclass(frozen=True)
class WhatsAppConfig:
    phone_id: str = ""
    token: str = ""
    verify_token: str = ""
    api_version: str = "v17.0"

    @property
    def is_configured(self) -> bool:
        return bool(self.phone_id and self.token)


@dataclass(frozen=True)
class EncryptionConfig:
    pii_enc_key: str = ""
    pii_key_id: str = "v1"

    @property
    def is_configured(self) -> bool:
        return bool(self.pii_enc_key)


@dataclass(frozen=True)
class AppConfig:
    """Master configuration — immutable after init."""

    app_name: str = "ClinicOS"
    debug: bool = False
    session_secret: str = "dev-secret-change-me"
    allow_dev_auth: bool = True
    base_url: str = "http://localhost:8000"

    db: DatabaseConfig = field(default_factory=DatabaseConfig)
    auth0: Auth0Config = field(default_factory=Auth0Config)
    google_oauth: GoogleOAuthConfig = field(default_factory=GoogleOAuthConfig)
    gemini: GeminiConfig = field(default_factory=GeminiConfig)
    whatsapp: WhatsAppConfig = field(default_factory=WhatsAppConfig)
    encryption: EncryptionConfig = field(default_factory=EncryptionConfig)


def load_config() -> AppConfig:
    """Build config from environment variables."""
    return AppConfig(
        app_name=os.getenv("APP_NAME", "ClinicOS"),
        debug=os.getenv("DEBUG", "false").lower() in ("1", "true", "yes"),
        session_secret=os.getenv("SESSION_SECRET", "dev-secret-change-me"),
        allow_dev_auth=os.getenv("ALLOW_DEV_AUTH", "true").lower() in ("1", "true", "yes"),
        base_url=os.getenv("BASE_URL", "http://localhost:8000"),
        db=DatabaseConfig(
            url=os.getenv("SUPABASE_DB_URL", ""),
        ),
        auth0=Auth0Config(
            domain=os.getenv("AUTH0_DOMAIN", ""),
            client_id=os.getenv("AUTH0_CLIENT_ID", ""),
            client_secret=os.getenv("AUTH0_CLIENT_SECRET", ""),
            callback_url=os.getenv("AUTH0_CALLBACK_URL", ""),
            audience=os.getenv("AUTH0_AUDIENCE", ""),
        ),
        google_oauth=GoogleOAuthConfig(
            client_id=os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            client_secret=os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            redirect_uri=os.getenv("GOOGLE_OAUTH_REDIRECT_URI", ""),
        ),
        gemini=GeminiConfig(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.2")),
        ),
        whatsapp=WhatsAppConfig(
            phone_id=os.getenv("PHONE_ID", ""),
            token=os.getenv("WHATSAPP_TOKEN", ""),
            verify_token=os.getenv("VERIFY_TOKEN", ""),
            api_version=os.getenv("WHATSAPP_API_VERSION", "v17.0"),
        ),
        encryption=EncryptionConfig(
            pii_enc_key=os.getenv("PII_ENC_KEY", ""),
            pii_key_id=os.getenv("PII_KEY_ID", "v1"),
        ),
    )


# Singleton — import `settings` anywhere
settings = load_config()
