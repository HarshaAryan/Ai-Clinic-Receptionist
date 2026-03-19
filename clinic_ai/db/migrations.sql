CREATE EXTENSION IF NOT EXISTS "pgcrypto";

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'appointment_status') THEN
        CREATE TYPE appointment_status AS ENUM ('PENDING', 'CONFIRMED', 'RESCHEDULED', 'CANCELLED', 'COMPLETED');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_type') THEN
        CREATE TYPE message_type AS ENUM ('TEXT', 'VOICE');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'message_direction') THEN
        CREATE TYPE message_direction AS ENUM ('INBOUND', 'OUTBOUND');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS clinics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    whatsapp_phone_id TEXT,
    api_keys JSONB,
    system_prompt TEXT,
    timezone TEXT DEFAULT 'UTC',
    specialization TEXT,
    contact_phone TEXT
);

CREATE TABLE IF NOT EXISTS clinic_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    auth0_sub TEXT UNIQUE NOT NULL,
    email TEXT,
    full_name TEXT,
    role TEXT NOT NULL DEFAULT 'CLINIC_ADMIN',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS clinic_settings (
    clinic_id UUID PRIMARY KEY REFERENCES clinics(id) ON DELETE CASCADE,
    working_days TEXT[] DEFAULT ARRAY['MON','TUE','WED','THU','FRI']::TEXT[],
    start_hour SMALLINT DEFAULT 10,
    end_hour SMALLINT DEFAULT 18,
    slot_duration_minutes SMALLINT DEFAULT 30,
    cancellation_window_hours SMALLINT DEFAULT 24,
    reminder_hours_before SMALLINT DEFAULT 24,
    tone TEXT,
    language TEXT,
    faq JSONB,
    escalation_keywords TEXT[],
    emergency_message TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS onboarding_state (
    clinic_id UUID PRIMARY KEY REFERENCES clinics(id) ON DELETE CASCADE,
    current_step SMALLINT NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'IN_PROGRESS',
    completed_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS patients (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    name_enc BYTEA,
    phone_enc BYTEA NOT NULL,
    email_enc BYTEA,
    phone_hash TEXT NOT NULL,
    tags TEXT[] DEFAULT ARRAY[]::TEXT[],
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS patients_phone_hash_unique ON patients (clinic_id, phone_hash);

CREATE TABLE IF NOT EXISTS appointments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    start_time TIMESTAMP NOT NULL,
    status appointment_status NOT NULL DEFAULT 'PENDING',
    calendar_event_id TEXT,
    source TEXT DEFAULT 'AI',
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS appointments_slot_unique ON appointments (clinic_id, start_time);
CREATE INDEX IF NOT EXISTS appointments_clinic_start_idx ON appointments (clinic_id, start_time);

CREATE TABLE IF NOT EXISTS conversation_threads (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    source TEXT NOT NULL DEFAULT 'WHATSAPP',
    takeover_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    last_message_at TIMESTAMP NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (clinic_id, patient_id, source)
);

CREATE INDEX IF NOT EXISTS conversation_threads_clinic_last_idx ON conversation_threads (clinic_id, last_message_at DESC);

CREATE TABLE IF NOT EXISTS conversation_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL,
    message_type message_type NOT NULL,
    direction message_direction NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW()
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'conversation_logs' AND column_name = 'thread_id'
    ) THEN
        ALTER TABLE conversation_logs ADD COLUMN thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS kb_entries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    content TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS voice_config (
    clinic_id UUID PRIMARY KEY REFERENCES clinics(id) ON DELETE CASCADE,
    provider TEXT NOT NULL DEFAULT 'BLAND',
    pathway_id TEXT NOT NULL,
    voice_id TEXT NOT NULL,
    settings_json JSONB,
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ─── Reminder logs (NudgeBot) ──────────────────────────────

CREATE TABLE IF NOT EXISTS reminder_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    appointment_id UUID NOT NULL REFERENCES appointments(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    hours_before SMALLINT NOT NULL DEFAULT 24,
    channel TEXT NOT NULL DEFAULT 'WHATSAPP',
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'SENT',
    sent_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS reminder_logs_clinic_idx ON reminder_logs (clinic_id, sent_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS reminder_logs_unique ON reminder_logs (appointment_id, hours_before);

-- ─── Emergency alerts (AlertBot) ───────────────────────────

CREATE TABLE IF NOT EXISTS emergency_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    thread_id UUID REFERENCES conversation_threads(id) ON DELETE SET NULL,
    channel TEXT NOT NULL DEFAULT 'WHATSAPP',
    urgency_level TEXT NOT NULL DEFAULT 'medium',
    emergency_type TEXT NOT NULL DEFAULT 'unknown',
    original_message TEXT NOT NULL,
    patient_phone TEXT,
    doctor_notified BOOLEAN NOT NULL DEFAULT FALSE,
    resolved BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    resolved_at TIMESTAMP
);

CREATE INDEX IF NOT EXISTS emergency_alerts_clinic_idx ON emergency_alerts (clinic_id, created_at DESC);

-- ─── Intent classification log (Orchestrator) ──────────────

CREATE TABLE IF NOT EXISTS intent_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    clinic_id UUID NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
    patient_id UUID REFERENCES patients(id) ON DELETE SET NULL,
    channel TEXT NOT NULL DEFAULT 'WHATSAPP',
    message_text TEXT NOT NULL,
    classified_intent TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 0,
    agent_used TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS intent_logs_clinic_idx ON intent_logs (clinic_id, created_at DESC);

-- ─── Unique constraints for doctor profiles ────────────────

CREATE UNIQUE INDEX IF NOT EXISTS clinic_admins_email_unique
    ON clinic_admins (LOWER(email)) WHERE email IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS clinics_contact_phone_unique
    ON clinics (contact_phone) WHERE contact_phone IS NOT NULL AND contact_phone != '';
