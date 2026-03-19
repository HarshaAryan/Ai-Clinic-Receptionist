import os
import base64
from services.encryption import encrypt_text, decrypt_text, hash_text


def test_encrypt_decrypt_roundtrip(monkeypatch):
    key = base64.b64encode(b"0" * 32).decode("utf-8")
    monkeypatch.setenv("PII_ENC_KEY", key)
    monkeypatch.setenv("PII_KEY_ID", "v1")

    blob = encrypt_text("hello")
    assert blob
    assert decrypt_text(blob) == "hello"


def test_hash_text():
    h = hash_text("123")
    assert h and len(h) == 64
