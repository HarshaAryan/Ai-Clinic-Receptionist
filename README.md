# 🏥 ClinicOS — AI-Powered Clinic Receptionist Platform

> **Replace your ₹15,000/month receptionist with ₹4,999/month AI.**

ClinicOS is a production-ready, multi-agent AI platform built for small health and dental clinics across India. It handles patient conversations, appointment booking, emergency detection, and automated reminders — all from a single, unified dashboard.

---

## ✨ What It Does

| Capability | Description |
|---|---|
| 📲 **WhatsApp Reception** | AI answers patient queries, books/reschedules/cancels appointments in Hindi, English, or Hinglish |
| 🚨 **Emergency Detection** | Instantly detects emergency keywords and alerts the doctor via SMS |
| 🔔 **Smart Reminders** | Sends automated WhatsApp reminders 24h and 2h before appointments |
| 📅 **Google Calendar Sync** | Checks live availability and creates calendar events automatically |
| 🔐 **PII Encryption** | Patient data encrypted at rest with AES-256-GCM |
| 🖥️ **Dashboard** | Live view of conversations, appointments, and patient records |

---

## 🤖 Agent Architecture

```
Incoming Message (WhatsApp / Web)
        │
        ▼
┌────────────────────────┐
│   Master Orchestrator  │  ← Gemini classifies intent
│  (agents/orchestrator) │
└──────────┬─────────────┘
           │
     ┌─────┼──────────┐
     ▼     ▼          ▼
Reception  Emergency  Reminder
  Agent     Agent      Agent
(ReceptBot)(AlertBot) (NudgeBot)
     │         │          │
     └─────────┴──────────┘
               │
        ┌──────▼──────┐
        │  PostgreSQL  │  (Supabase)
        │  + Google    │  (Calendar)
        │  + WhatsApp  │  (Meta Cloud API)
        └─────────────┘
```

### Agents

| Agent | File | Trigger | Responsibility |
|---|---|---|---|
| **ReceptBot** | `agents/reception.py` | Inbound WhatsApp message | Book · Reschedule · Cancel · Answer queries |
| **AlertBot** | `agents/emergency.py` | Emergency keyword in any message | Detect emergency → alert doctor → reassure patient |
| **NudgeBot** | `agents/reminder.py` | Scheduler (24h + 2h before appointment) | Send WhatsApp reminders |
| **Orchestrator** | `agents/orchestrator.py` | Every inbound message | Classify intent → route to correct agent |

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Backend** | FastAPI · Python 3.11 · Uvicorn |
| **Database** | PostgreSQL via Supabase |
| **AI / LLM** | Google Gemini 1.5 Pro |
| **Messaging** | Meta WhatsApp Cloud API |
| **Calendar** | Google Calendar API |
| **Auth** | Auth0 + session-based |
| **Encryption** | AES-256-GCM (PII) |
| **Templates** | Jinja2 |
| **Testing** | Pytest |
| **Scheduling** | APScheduler |

---

## 📁 Project Structure

```
clinic_ai/
├── app.py                    # FastAPI entrypoint & app factory
├── config.py                 # Centralised settings (env-driven)
├── models.py                 # Pydantic domain models
│
├── agents/                   # 🤖 Agentic layer
│   ├── base_agent.py         # BaseAgent ABC + AgentResult contract
│   ├── orchestrator.py       # Master intent classifier
│   ├── reception.py          # ReceptBot — booking & FAQ
│   ├── emergency.py          # AlertBot — emergency detection
│   └── reminder.py           # NudgeBot — reminder dispatch
│
├── services/                 # Business logic & external integrations
│   ├── gemini.py             # Multi-prompt Gemini AI service
│   ├── whatsapp.py           # WhatsApp message sender
│   ├── calendar.py           # Google Calendar integration
│   ├── slots.py              # Available slot generator
│   ├── reminder.py           # Reminder scheduling service
│   ├── encryption.py         # AES-GCM PII encryption
│   ├── auth.py               # JWT verification + session
│   ├── kb.py                 # Knowledge base renderer
│   └── logger.py             # Structured logging
│
├── db/
│   ├── migrations.sql        # Full Supabase schema
│   ├── session.py            # Async connection pool
│   └── queries.py            # All SQL queries
│
├── routers/                  # FastAPI route handlers
│   ├── api.py                # REST API (inbox, appointments, patients)
│   ├── auth.py               # Auth0 / dev auth
│   ├── calendar.py           # Google Calendar OAuth
│   ├── dashboard.py          # Dashboard page
│   ├── home.py               # Landing page
│   ├── reminders.py          # Reminder trigger endpoints
│   ├── setup.py              # Onboarding wizard
│   └── whatsapp.py           # WhatsApp webhook → orchestrator pipeline
│
├── templates/                # Jinja2 HTML templates
├── test/                     # Pytest test suite
├── .env.example              # Environment variable reference
└── requirements.txt
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project (free tier works)
- A [Google Cloud](https://console.cloud.google.com) project with **Gemini API** and **Calendar API** enabled
- A [Meta Developer](https://developers.facebook.com) app with WhatsApp Cloud API access
- An [Auth0](https://auth0.com) tenant

---

### 1 · Clone & Install

```bash
git clone <repo-url>
cd clinic_ai
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### 2 · Configure Environment

```bash
cp .env.example .env
# Open .env and fill in all required keys (see table below)
```

#### Required Environment Variables

| Variable | Description |
|---|---|
| `SUPABASE_DB_URL` | PostgreSQL connection string from Supabase |
| `GEMINI_API_KEY` | Google AI Studio API key |
| `GEMINI_MODEL` | Model to use (default: `gemini-1.5-pro`) |
| `WHATSAPP_TOKEN` | Meta WhatsApp Cloud API bearer token |
| `PHONE_ID` | WhatsApp Business phone number ID |
| `VERIFY_TOKEN` | Your chosen webhook verify token |
| `GOOGLE_OAUTH_CLIENT_ID` | Google OAuth 2.0 client ID (Calendar) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | Google OAuth 2.0 client secret |
| `AUTH0_DOMAIN` | Your Auth0 tenant domain |
| `AUTH0_CLIENT_ID` | Auth0 application client ID |
| `AUTH0_CLIENT_SECRET` | Auth0 application client secret |
| `PII_ENC_KEY` | 32-byte AES key (base64 or hex) for PII encryption |
| `SESSION_SECRET` | Random string for session signing |

### 3 · Database Setup

Go to your Supabase project → **SQL Editor** and run:

```sql
-- Run the entire file:
db/migrations.sql
```

### 4 · Run Locally

```bash
uvicorn app:app --reload
```

The app will be live at **http://localhost:8000**

### 5 · Connect WhatsApp Webhook

In your Meta Developer Console, set the webhook callback URL to:

```
https://<your-domain>/webhook/whatsapp
```

Use the same `VERIFY_TOKEN` value you set in `.env`.

> **Tip for local development:** Use [ngrok](https://ngrok.com) to expose your local server — `ngrok http 8000`

---

## 🌐 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Landing page |
| `GET` | `/dashboard` | Main dashboard |
| `POST` | `/webhook/whatsapp` | WhatsApp inbound handler (Meta webhook) |
| `GET` | `/api/inbox/threads` | List conversation threads |
| `GET` | `/api/appointments` | List appointments |
| `POST` | `/api/appointments` | Create appointment |
| `GET` | `/api/patients` | List patients |
| `POST` | `/api/reminders/send` | Trigger reminders for the current clinic |
| `POST` | `/api/reminders/cron` | Cron endpoint — triggers reminders for all clinics |
| `GET` | `/calendar/connect` | Initiate Google Calendar OAuth flow |

---

## 🧪 Tests

```bash
pytest -v
```

Tests live in the `test/` directory and cover agent logic, slot generation, and API endpoints.

---

## ☁️ Deployment

### Render / Railway (Recommended)

```bash
uvicorn app:app --host 0.0.0.0 --port $PORT
```

Set all environment variables in the platform's dashboard. No `Dockerfile` needed — Render supports Python natively.

### Docker (Optional)

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

---

## 🔒 Security Notes

- `.env` is git-ignored — **never commit secrets**
- All patient PII is encrypted at rest using AES-256-GCM before writing to the database
- JWT tokens are verified on every protected route
- Use HTTPS in production (Render provides free TLS)

---

## 📈 Pricing Model

| Plan | Price | Includes |
|---|---|---|
| **Starter** | ₹4,999 / month | WhatsApp reception, reminders, emergency alerts |
| **Growth** | ₹9,999 / month | Everything + social media agent |

> 200 happy clinics = ₹1 Cr/month 🚀

---

## 🗺️ Roadmap

- [x] ReceptBot — WhatsApp appointment booking
- [x] AlertBot — Emergency detection & doctor alerts
- [x] NudgeBot — Automated reminders (24h + 2h)
- [x] Google Calendar sync
- [x] Auth0 authentication
- [x] AES-256-GCM PII encryption
- [x] Unified dashboard
- [ ] VoiceBot — Incoming call handling (VAPI.ai)
- [ ] BuzzBot — Social media scheduler (Instagram / Twitter)
- [ ] WelcomeBot — Automated onboarding agent
- [ ] Multi-clinic support dashboard

---

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit your changes: `git commit -m "feat: add your feature"`
4. Push and open a PR

---

## 📄 License

MIT © 2024 ClinicOS