import os
import base64
import pytest
from datetime import datetime, timedelta
from db.session import db_cursor
from services.encryption import encrypt_text, hash_text


def _require_db():
    url = os.getenv("SUPABASE_DB_URL", "")
    if not url or "your-password" in url or "your-project" in url:
        pytest.skip("SUPABASE_DB_URL not set or contains placeholder")


def test_appointment_conflict(monkeypatch):
    _require_db()
    key = base64.b64encode(b"1" * 32).decode("utf-8")
    monkeypatch.setenv("PII_ENC_KEY", key)

    with db_cursor() as cur:
        cur.execute("INSERT INTO clinics (id, name) VALUES (gen_random_uuid(), 'Test Clinic') RETURNING id")
        clinic_id = cur.fetchone()["id"]
        phone = "+10001112222"
        cur.execute(
            """
            INSERT INTO patients (id, clinic_id, name_enc, phone_enc, email_enc, phone_hash, tags)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                str(clinic_id),
                encrypt_text("Test"),
                encrypt_text(phone),
                None,
                hash_text(phone),
                [],
            ),
        )
        patient_id = cur.fetchone()["id"]
        start = datetime.utcnow() + timedelta(days=1)
        cur.execute(
            """
            INSERT INTO appointments (id, clinic_id, patient_id, start_time, status)
            VALUES (gen_random_uuid(), %s, %s, %s, 'CONFIRMED')
            """,
            (str(clinic_id), str(patient_id), start),
        )

        with pytest.raises(Exception):
            cur.execute(
                """
                INSERT INTO appointments (id, clinic_id, patient_id, start_time, status)
                VALUES (gen_random_uuid(), %s, %s, %s, 'PENDING')
                """,
                (str(clinic_id), str(patient_id), start),
            )
