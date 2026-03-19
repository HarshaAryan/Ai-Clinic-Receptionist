import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from db.session import db_cursor
from services.encryption import decrypt_text, encrypt_text, hash_text


def _safe_decrypt(value):
    if value is None:
        return None
    try:
        return decrypt_text(value)
    except Exception:
        return None


def _normalize_clinic_id(clinic_id: Any) -> str:
    return str(clinic_id)


def get_clinic_by_phone_id(phone_id: str) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM clinics WHERE whatsapp_phone_id = %s", (phone_id,))
        return cur.fetchone()


def get_clinic_by_id(clinic_id: Any) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT * FROM clinics WHERE id = %s", (cid,))
        return cur.fetchone()


def get_kb_entries(clinic_id: Any) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            "SELECT title, content FROM kb_entries WHERE clinic_id = %s ORDER BY title",
            (cid,),
        )
        return cur.fetchall() or []


def find_patient_by_phone(clinic_id: Any, phone: str) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    phone_hash = hash_text(phone)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            "SELECT * FROM patients WHERE clinic_id = %s AND phone_hash = %s",
            (cid, phone_hash),
        )
        return cur.fetchone()


def create_patient(clinic_id: Any, name: Optional[str], phone: str, email: Optional[str] = None) -> Dict[str, Any]:
    cid = _normalize_clinic_id(clinic_id)
    name_enc = encrypt_text(name) if name else None
    phone_enc = encrypt_text(phone)
    email_enc = encrypt_text(email) if email else None
    phone_hash = hash_text(phone)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            INSERT INTO patients (id, clinic_id, name_enc, phone_enc, email_enc, phone_hash, tags)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s)
            RETURNING *
            """,
            (cid, name_enc, phone_enc, email_enc, phone_hash, []),
        )
        return cur.fetchone()


def find_or_create_patient(clinic_id: Any, phone: str, name: Optional[str] = None) -> Dict[str, Any]:
    patient = find_patient_by_phone(clinic_id, phone)
    if patient:
        return patient
    return create_patient(clinic_id, name, phone)


def get_or_create_thread(clinic_id: Any, patient_id: Any, source: str = "WHATSAPP") -> Dict[str, Any]:
    cid = _normalize_clinic_id(clinic_id)
    pid = str(patient_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            INSERT INTO conversation_threads (id, clinic_id, patient_id, source)
            VALUES (gen_random_uuid(), %s, %s, %s)
            ON CONFLICT (clinic_id, patient_id, source)
            DO UPDATE SET updated_at = NOW()
            RETURNING *
            """,
            (cid, pid, source),
        )
        return cur.fetchone()


def set_thread_takeover(clinic_id: Any, thread_id: Any, takeover_enabled: bool) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            UPDATE conversation_threads
            SET takeover_enabled = %s, updated_at = NOW()
            WHERE id = %s AND clinic_id = %s
            RETURNING *
            """,
            (takeover_enabled, str(thread_id), cid),
        )
        return cur.fetchone()


def is_thread_takeover_enabled(clinic_id: Any, thread_id: Any) -> bool:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            "SELECT takeover_enabled FROM conversation_threads WHERE id = %s AND clinic_id = %s",
            (str(thread_id), cid),
        )
        row = cur.fetchone()
        return bool(row and row.get("takeover_enabled"))


def log_message(
    clinic_id: Any,
    patient_id: Any,
    thread_id: Any,
    message_type: str,
    direction: str,
    content: str,
    timestamp: Optional[datetime] = None,
) -> None:
    cid = _normalize_clinic_id(clinic_id)
    pid = str(patient_id)
    tid = str(thread_id) if thread_id else None
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            INSERT INTO conversation_logs (id, clinic_id, patient_id, thread_id, message_type, direction, content, timestamp)
            VALUES (gen_random_uuid(), %s, %s, %s, %s, %s, %s, COALESCE(%s, NOW()))
            """,
            (cid, pid, tid, message_type, direction, content, timestamp),
        )
        if tid:
            cur.execute(
                """
                UPDATE conversation_threads
                SET last_message_at = NOW(), updated_at = NOW()
                WHERE id = %s AND clinic_id = %s
                """,
                (tid, cid),
            )


def get_last_messages(clinic_id: Any, patient_id: Any, limit: int = 5) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            SELECT direction, content, timestamp
            FROM conversation_logs
            WHERE clinic_id = %s AND patient_id = %s
            ORDER BY timestamp DESC
            LIMIT %s
            """,
            (cid, str(patient_id), limit),
        )
        rows = cur.fetchall() or []
    return list(reversed(rows))


def create_appointment(clinic_id: Any, patient_id: Any, start_time: datetime, status: str = "PENDING") -> Dict[str, Any]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            INSERT INTO appointments (id, clinic_id, patient_id, start_time, status)
            VALUES (gen_random_uuid(), %s, %s, %s, %s)
            RETURNING *
            """,
            (cid, str(patient_id), start_time, status),
        )
        return cur.fetchone()


def update_appointment_calendar_id(clinic_id: Any, appointment_id: Any, calendar_event_id: str, status: str = "CONFIRMED") -> None:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            UPDATE appointments
            SET calendar_event_id = %s, status = %s, updated_at = NOW()
            WHERE id = %s AND clinic_id = %s
            """,
            (calendar_event_id, status, str(appointment_id), cid),
        )


def get_upcoming_appointments(clinic_id: Any, limit: int = 10) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            SELECT a.*, p.name_enc, p.phone_enc
            FROM appointments a
            JOIN patients p ON p.id = a.patient_id
            WHERE a.clinic_id = %s AND a.start_time >= NOW()
            ORDER BY a.start_time ASC
            LIMIT %s
            """,
            (cid, limit),
        )
        rows = cur.fetchall() or []
    for row in rows:
        row["patient_name"] = _safe_decrypt(row.get("name_enc")) or "Unknown"
        row["patient_phone"] = _safe_decrypt(row.get("phone_enc")) or "Unavailable"
    return rows


def get_metrics(clinic_id: Any) -> Dict[str, int]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT COUNT(*) AS cnt FROM appointments WHERE clinic_id = %s", (cid,))
        appts = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM conversation_logs WHERE clinic_id = %s", (cid,))
        msgs = cur.fetchone()["cnt"]
        cur.execute("SELECT COUNT(*) AS cnt FROM patients WHERE clinic_id = %s", (cid,))
        patients = cur.fetchone()["cnt"]
    return {"appointments": appts, "messages": msgs, "patients": patients}


def get_clinic_google_tokens(clinic_id: Any) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT api_keys FROM clinics WHERE id = %s", (cid,))
        row = cur.fetchone()
        if not row or not row.get("api_keys"):
            return None
        return row["api_keys"].get("google_oauth")


def store_clinic_google_tokens(clinic_id: Any, token_payload: Dict[str, Any]) -> None:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            UPDATE clinics
            SET api_keys = COALESCE(api_keys, '{}'::jsonb) || jsonb_build_object('google_oauth', %s::jsonb)
            WHERE id = %s
            """,
            (json.dumps(token_payload), cid),
        )


def get_admin_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Look up a doctor by email address (case-insensitive)."""
    with db_cursor() as cur:
        cur.execute(
            "SELECT * FROM clinic_admins WHERE LOWER(email) = LOWER(%s)",
            (email.strip(),),
        )
        admin = cur.fetchone()
        if not admin:
            return None
        cur.execute("SELECT * FROM clinics WHERE id = %s", (str(admin["clinic_id"]),))
        clinic = cur.fetchone()
        state = get_onboarding_state(admin["clinic_id"])
        return {"admin": admin, "clinic": clinic, "onboarding": state}


def check_phone_unique(phone: str, exclude_clinic_id: Optional[str] = None) -> bool:
    """Return True if the contact_phone is not already used by another clinic."""
    if not phone or not phone.strip():
        return True
    with db_cursor() as cur:
        if exclude_clinic_id:
            cur.execute(
                "SELECT id FROM clinics WHERE contact_phone = %s AND id != %s",
                (phone.strip(), exclude_clinic_id),
            )
        else:
            cur.execute(
                "SELECT id FROM clinics WHERE contact_phone = %s",
                (phone.strip(),),
            )
        return cur.fetchone() is None


def get_or_create_admin_clinic(auth0_sub: str, email: Optional[str], full_name: Optional[str]) -> Dict[str, Any]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM clinic_admins WHERE auth0_sub = %s", (auth0_sub,))
        admin = cur.fetchone()
        if admin:
            cur.execute("SELECT * FROM clinics WHERE id = %s", (str(admin["clinic_id"]),))
            clinic = cur.fetchone()
            state = get_onboarding_state(admin["clinic_id"])
            return {"admin": admin, "clinic": clinic, "onboarding": state}

        clinic_name = f"{(full_name or 'New Doctor').strip()} Clinic"
        cur.execute(
            """
            INSERT INTO clinics (id, name)
            VALUES (gen_random_uuid(), %s)
            RETURNING *
            """,
            (clinic_name,),
        )
        clinic = cur.fetchone()

        cur.execute(
            """
            INSERT INTO clinic_admins (id, clinic_id, auth0_sub, email, full_name)
            VALUES (gen_random_uuid(), %s, %s, %s, %s)
            RETURNING *
            """,
            (str(clinic["id"]), auth0_sub, email, full_name),
        )
        admin = cur.fetchone()

        cur.execute(
            """
            INSERT INTO clinic_settings (clinic_id)
            VALUES (%s)
            ON CONFLICT (clinic_id) DO NOTHING
            """,
            (str(clinic["id"]),),
        )
        cur.execute(
            """
            INSERT INTO onboarding_state (clinic_id, current_step, status)
            VALUES (%s, 1, 'IN_PROGRESS')
            ON CONFLICT (clinic_id) DO NOTHING
            """,
            (str(clinic["id"]),),
        )

        state = get_onboarding_state(clinic["id"])
        return {"admin": admin, "clinic": clinic, "onboarding": state}


def get_admin_clinic_by_sub(auth0_sub: str) -> Optional[Dict[str, Any]]:
    with db_cursor() as cur:
        cur.execute("SELECT * FROM clinic_admins WHERE auth0_sub = %s", (auth0_sub,))
        admin = cur.fetchone()
        if not admin:
            return None
        cur.execute("SELECT * FROM clinics WHERE id = %s", (str(admin["clinic_id"]),))
        clinic = cur.fetchone()
        state = get_onboarding_state(admin["clinic_id"])
        return {"admin": admin, "clinic": clinic, "onboarding": state}


def update_clinic_profile(clinic_id: Any, clinic_name: Optional[str], specialization: Optional[str], contact_phone: Optional[str]) -> None:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            UPDATE clinics
            SET name = COALESCE(%s, name),
                specialization = COALESCE(%s, specialization),
                contact_phone = COALESCE(%s, contact_phone)
            WHERE id = %s
            """,
            (
                clinic_name.strip() if clinic_name else None,
                specialization.strip() if specialization else None,
                contact_phone.strip() if contact_phone else None,
                cid,
            ),
        )


def get_onboarding_state(clinic_id: Any) -> Dict[str, Any]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT * FROM onboarding_state WHERE clinic_id = %s", (cid,))
        row = cur.fetchone()
        if row:
            return row
        cur.execute(
            "INSERT INTO onboarding_state (clinic_id, current_step, status) VALUES (%s, 1, 'IN_PROGRESS') RETURNING *",
            (cid,),
        )
        return cur.fetchone()


def save_onboarding_step(clinic_id: Any, step: int, payload: Dict[str, Any]) -> Dict[str, Any]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        if step == 1:
            cur.execute(
                """
                UPDATE clinics
                SET name = %s,
                    timezone = %s,
                    specialization = %s,
                    contact_phone = %s
                WHERE id = %s
                """,
                (
                    payload.get("clinic_name") or "Clinic",
                    payload.get("timezone") or "UTC",
                    payload.get("specialization"),
                    payload.get("contact_phone"),
                    cid,
                ),
            )
        elif step == 2:
            cur.execute(
                """
                INSERT INTO clinic_settings (clinic_id, working_days, start_hour, end_hour, slot_duration_minutes, cancellation_window_hours, reminder_hours_before)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (clinic_id)
                DO UPDATE SET
                    working_days = EXCLUDED.working_days,
                    start_hour = EXCLUDED.start_hour,
                    end_hour = EXCLUDED.end_hour,
                    slot_duration_minutes = EXCLUDED.slot_duration_minutes,
                    cancellation_window_hours = EXCLUDED.cancellation_window_hours,
                    reminder_hours_before = EXCLUDED.reminder_hours_before,
                    updated_at = NOW()
                """,
                (
                    cid,
                    payload.get("working_days") or ["MON", "TUE", "WED", "THU", "FRI"],
                    int(payload.get("start_hour") or 10),
                    int(payload.get("end_hour") or 18),
                    int(payload.get("slot_duration_minutes") or 30),
                    int(payload.get("cancellation_window_hours") or 24),
                    int(payload.get("reminder_hours_before") or 24),
                ),
            )
        elif step == 3:
            cur.execute(
                """
                INSERT INTO clinic_settings (clinic_id, tone, language, faq, escalation_keywords, emergency_message)
                VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                ON CONFLICT (clinic_id)
                DO UPDATE SET
                    tone = EXCLUDED.tone,
                    language = EXCLUDED.language,
                    faq = EXCLUDED.faq,
                    escalation_keywords = EXCLUDED.escalation_keywords,
                    emergency_message = EXCLUDED.emergency_message,
                    updated_at = NOW()
                """,
                (
                    cid,
                    payload.get("tone") or "Professional",
                    payload.get("language") or "English",
                    json.dumps(payload.get("faq") or []),
                    payload.get("escalation_keywords") or ["emergency", "urgent", "pain"],
                    payload.get("emergency_message") or "If this is an emergency, please call 112/911 immediately.",
                ),
            )
        elif step == 4:
            cur.execute(
                """
                INSERT INTO voice_config (clinic_id, provider, pathway_id, voice_id, settings_json)
                VALUES (%s, 'BLAND', %s, %s, %s::jsonb)
                ON CONFLICT (clinic_id)
                DO UPDATE SET
                    provider = 'BLAND',
                    pathway_id = EXCLUDED.pathway_id,
                    voice_id = EXCLUDED.voice_id,
                    settings_json = EXCLUDED.settings_json,
                    updated_at = NOW()
                """,
                (
                    cid,
                    payload.get("pathway_id"),
                    payload.get("voice_id"),
                    json.dumps(
                        {
                            "language": payload.get("voice_language"),
                            "gender": payload.get("voice_gender"),
                            "tone": payload.get("voice_tone"),
                        }
                    ),
                ),
            )

        status = "COMPLETED" if step >= 4 else "IN_PROGRESS"
        cur.execute(
            """
            INSERT INTO onboarding_state (clinic_id, current_step, status, completed_at)
            VALUES (%s, %s, %s, CASE WHEN %s='COMPLETED' THEN NOW() ELSE NULL END)
            ON CONFLICT (clinic_id)
            DO UPDATE SET
                current_step = GREATEST(onboarding_state.current_step, EXCLUDED.current_step),
                status = CASE WHEN EXCLUDED.status='COMPLETED' THEN 'COMPLETED' ELSE onboarding_state.status END,
                completed_at = CASE WHEN EXCLUDED.status='COMPLETED' THEN NOW() ELSE onboarding_state.completed_at END
            RETURNING *
            """,
            (cid, step, status, status),
        )
        return cur.fetchone()


def get_clinic_settings(clinic_id: Any) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT * FROM clinic_settings WHERE clinic_id = %s", (cid,))
        return cur.fetchone()


def get_voice_config(clinic_id: Any) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT * FROM voice_config WHERE clinic_id = %s", (cid,))
        return cur.fetchone()


def list_threads(clinic_id: Any, limit: int = 50) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            SELECT t.*, p.name_enc, p.phone_enc,
                   (SELECT content FROM conversation_logs l WHERE l.thread_id = t.id ORDER BY l.timestamp DESC LIMIT 1) AS last_message
            FROM conversation_threads t
            JOIN patients p ON p.id = t.patient_id
            WHERE t.clinic_id = %s
            ORDER BY t.last_message_at DESC
            LIMIT %s
            """,
            (cid, limit),
        )
        rows = cur.fetchall() or []
    for row in rows:
        row["patient_name"] = _safe_decrypt(row.get("name_enc")) or "Unknown"
        row["patient_phone"] = _safe_decrypt(row.get("phone_enc")) or "Unavailable"
    return rows


def get_thread_messages(clinic_id: Any, thread_id: Any, limit: int = 100) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            SELECT * FROM conversation_logs
            WHERE clinic_id = %s AND thread_id = %s
            ORDER BY timestamp ASC
            LIMIT %s
            """,
            (cid, str(thread_id), limit),
        )
        return cur.fetchall() or []


def list_appointments(clinic_id: Any, status: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        if status:
            cur.execute(
                """
                SELECT a.*, p.name_enc, p.phone_enc
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                WHERE a.clinic_id = %s AND a.status = %s
                ORDER BY a.start_time ASC
                LIMIT %s
                """,
                (cid, status, limit),
            )
        else:
            cur.execute(
                """
                SELECT a.*, p.name_enc, p.phone_enc
                FROM appointments a
                JOIN patients p ON p.id = a.patient_id
                WHERE a.clinic_id = %s
                ORDER BY a.start_time ASC
                LIMIT %s
                """,
                (cid, limit),
            )
        rows = cur.fetchall() or []
    for row in rows:
        row["patient_name"] = _safe_decrypt(row.get("name_enc")) or "Unknown"
        row["patient_phone"] = _safe_decrypt(row.get("phone_enc")) or "Unavailable"
    return rows


def patch_appointment(clinic_id: Any, appointment_id: Any, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    updates = []
    params: List[Any] = []
    if payload.get("status"):
        updates.append("status = %s")
        params.append(payload["status"])
    if payload.get("start_time"):
        updates.append("start_time = %s")
        params.append(payload["start_time"])
    if payload.get("notes") is not None:
        updates.append("notes = %s")
        params.append(payload["notes"])
    if not updates:
        return None
    updates.append("updated_at = NOW()")
    params.extend([str(appointment_id), cid])
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            f"UPDATE appointments SET {', '.join(updates)} WHERE id = %s AND clinic_id = %s RETURNING *",
            tuple(params),
        )
        return cur.fetchone()


def list_patients(clinic_id: Any, limit: int = 200) -> List[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute(
            """
            SELECT p.*,
                   (SELECT MAX(timestamp) FROM conversation_logs l WHERE l.patient_id = p.id AND l.clinic_id = p.clinic_id) AS last_interaction,
                   (SELECT MIN(start_time) FROM appointments a WHERE a.patient_id = p.id AND a.clinic_id = p.clinic_id AND a.start_time >= NOW()) AS next_appointment
            FROM patients p
            WHERE p.clinic_id = %s
            ORDER BY p.created_at DESC
            LIMIT %s
            """,
            (cid, limit),
        )
        rows = cur.fetchall() or []
    for row in rows:
        row["name"] = _safe_decrypt(row.get("name_enc")) or "Unknown"
        row["phone"] = _safe_decrypt(row.get("phone_enc")) or "Unavailable"
        row["email"] = _safe_decrypt(row.get("email_enc"))
    return rows


def get_patient(clinic_id: Any, patient_id: Any) -> Optional[Dict[str, Any]]:
    cid = _normalize_clinic_id(clinic_id)
    with db_cursor(clinic_id=cid) as cur:
        cur.execute("SELECT * FROM patients WHERE id = %s AND clinic_id = %s", (str(patient_id), cid))
        row = cur.fetchone()
        if not row:
            return None
        row["name"] = _safe_decrypt(row.get("name_enc")) or "Unknown"
        row["phone"] = _safe_decrypt(row.get("phone_enc")) or "Unavailable"
        row["email"] = _safe_decrypt(row.get("email_enc"))
        return row
