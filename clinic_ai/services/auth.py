import os
import time
import requests
from jose import jwt
from typing import Dict, Any
from starlette.requests import Request
from starlette.exceptions import HTTPException

JWKS_CACHE = {"fetched_at": 0, "jwks": None}


def _auth0_domain() -> str:
    domain = os.getenv("AUTH0_DOMAIN")
    if not domain:
        raise RuntimeError("AUTH0_DOMAIN not set")
    return domain


def _auth0_audience() -> str:
    return os.getenv("AUTH0_AUDIENCE", "")


def _get_jwks() -> Dict[str, Any]:
    now = time.time()
    if JWKS_CACHE["jwks"] and now - JWKS_CACHE["fetched_at"] < 3600:
        return JWKS_CACHE["jwks"]
    url = f"https://{_auth0_domain()}/.well-known/jwks.json"
    jwks = requests.get(url, timeout=10).json()
    JWKS_CACHE["jwks"] = jwks
    JWKS_CACHE["fetched_at"] = now
    return jwks


def verify_jwt(token: str) -> Dict[str, Any]:
    jwks = _get_jwks()
    unverified_header = jwt.get_unverified_header(token)
    rsa_key = None
    for key in jwks.get("keys", []):
        if key.get("kid") == unverified_header.get("kid"):
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
            break
    if not rsa_key:
        raise HTTPException(status_code=401, detail="Invalid token")

    options = {"verify_aud": bool(_auth0_audience())}
    payload = jwt.decode(
        token,
        rsa_key,
        algorithms=["RS256"],
        audience=_auth0_audience() or None,
        issuer=f"https://{_auth0_domain()}/",
        options=options,
    )
    return payload


def get_current_user(request: Request) -> Dict[str, Any]:
    if request.session.get("user"):
        return request.session["user"]

    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        return verify_jwt(token)

    raise HTTPException(status_code=401, detail="Not authenticated")


def get_current_clinic_id(request: Request) -> str:
    user = get_current_user(request)
    clinic_id = request.session.get("clinic_id") or user.get("clinic_id") or user.get("https://antigravity/clinic_id")
    if not clinic_id:
        raise HTTPException(status_code=403, detail="Clinic context missing")
    return str(clinic_id)
