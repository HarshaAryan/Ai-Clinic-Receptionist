import base64
import json
import os
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

KEY_ENV = "PII_ENC_KEY"
KEY_ID_ENV = "PII_KEY_ID"


def _load_key():
    key = os.getenv(KEY_ENV)
    if not key:
        raise RuntimeError("PII_ENC_KEY is not set")

    # Accept base64, hex, or raw 32-byte string
    try:
        if len(key) in (44, 48) and all(c.isalnum() or c in "+/=" for c in key):
            raw = base64.b64decode(key)
        elif all(c in "0123456789abcdefABCDEF" for c in key) and len(key) in (64, 96):
            raw = bytes.fromhex(key)
        else:
            raw = key.encode("utf-8")
    except Exception as exc:
        raise RuntimeError("Invalid PII_ENC_KEY format") from exc

    if len(raw) not in (32,):
        raise RuntimeError("PII_ENC_KEY must be 32 bytes")
    return raw


def _get_kid():
    return os.getenv(KEY_ID_ENV, "v1")


def encrypt_text(plaintext: str) -> bytes:
    if plaintext is None:
        return None
    key = _load_key()
    kid = _get_kid()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = {
        "kid": kid,
        "nonce": base64.b64encode(nonce).decode("utf-8"),
        "ct": base64.b64encode(ciphertext).decode("utf-8"),
    }
    return json.dumps(payload).encode("utf-8")


def decrypt_text(blob: bytes) -> str:
    if blob is None:
        return None
    key = _load_key()
    payload = json.loads(blob.decode("utf-8"))
    nonce = base64.b64decode(payload["nonce"])
    ct = base64.b64decode(payload["ct"])
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ct, None)
    return plaintext.decode("utf-8")


def hash_text(plaintext: str) -> str:
    if plaintext is None:
        return None
    return hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
