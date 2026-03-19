# 🏥 ClinicOS — AI-Powered Clinic Growth Platform
## Master Architecture & Agent Design Guide
### Target: Small Health & Dental Clinics in India | Built with Google Gemini + n8n + Python

---

## 🎯 THE VISION

A single platform where one doctor/clinic owner logs in and gets:
- All patient conversations (calls, DMs, comments) in ONE dashboard
- AI agents handling reception, reminders, marketing, emergencies
- Zero receptionist needed. Zero missed leads.

**Revenue Model for YOU:**
- ₹4,999/month per clinic (starter)
- ₹9,999/month per clinic (growth - includes social media)
- 200 clinics = ₹1 Cr/month → Millionaire ✅

---

## 🏗️ SYSTEM ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────┐
│                     CLINICOS PLATFORM                        │
│                                                             │
│  ┌──────────┐    ┌─────────────────────────────────────┐   │
│  │  Web App │    │        MASTER ORCHESTRATOR           │   │
│  │(Next.js/ │◄──►│    (Google Gemini + n8n Webhook)     │   │
│  │ Firebase)│    │   Decides which agent handles what   │   │
│  └──────────┘    └──────────────┬──────────────────────┘   │
│                                 │                            │
│         ┌───────────────────────┼──────────────────┐        │
│         ▼               ▼       ▼        ▼          ▼       │
│   ┌──────────┐  ┌──────────┐ ┌──────┐ ┌──────┐ ┌──────┐   │
│   │RECEPTION │  │MARKETING │ │REMIND│ │SOCIAL│ │EMERG │   │
│   │  AGENT   │  │  AGENT   │ │ER    │ │MEDIA │ │ENCY  │   │
│   │          │  │          │ │AGENT │ │AGENT │ │AGENT │   │
│   └──────────┘  └──────────┘ └──────┘ └──────┘ └──────┘   │
│         │              │         │        │         │        │
│         └──────────────┴─────────┴────────┴─────────┘        │
│                              │                               │
│                    ┌─────────▼──────────┐                   │
│                    │  UNIFIED INBOX DB  │                   │
│                    │  (Firebase/Sheets) │                   │
│                    └────────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 TECH STACK (Zero/Low Cost)

| Layer | Tool | Cost |
|-------|------|------|
| Frontend | HTML/CSS/JS or Firebase Hosting | Free |
| Auth | Firebase Auth | Free |
| Database | Firebase Firestore + Google Sheets | Free |
| Orchestrator | n8n (self-hosted on Railway/Render) | Free tier |
| AI Brain | Google Gemini 1.5 Flash API | Free tier (generous) |
| Calls | Twilio (trial) → later VAPI.ai | Free trial |
| WhatsApp | Twilio WhatsApp Sandbox | Free trial |
| Social Media | Meta Graph API + Twitter API v2 | Free |
| Scheduler | n8n cron nodes | Free |
| Hosting | Railway / Render | Free tier |

---

## 🤖 THE 6 AGENTS

### AGENT 1: RECEPTION AGENT (ReceptBot)
**Job:** Answer patient queries via WhatsApp, handle appointment booking, collect patient info
**Triggers:** Incoming WhatsApp message → n8n webhook
**Tools it uses:** Google Calendar API, Firestore, Gemini
**n8n Flow:** WhatsApp → Parse message → Gemini classify intent → Book/Reschedule/FAQ → Reply → Log to DB

---

### AGENT 2: REMINDER AGENT (NudgeBot)
**Job:** Send appointment reminders 24hr + 2hr before, post-visit follow-up
**Triggers:** n8n Cron (every hour), checks upcoming appointments
**Tools:** Firestore, WhatsApp API, Gmail
**n8n Flow:** Cron → Query appointments due → Send WhatsApp reminder → Log sent status

---

### AGENT 3: SOCIAL MEDIA AGENT (BuzzBot)
**Job:** Post clinic content on Instagram/Twitter, reply to comments, DM leads
**Triggers:** Scheduled posts (3x/week) + incoming DM/comment webhooks
**Tools:** Meta Graph API, Twitter API, Gemini (content generation)
**n8n Flow:** Schedule → Gemini generates post → Post to IG/Twitter → Monitor comments → Auto-reply

---

### AGENT 4: CALL AGENT (VoiceBot)
**Job:** Answer incoming patient calls, take messages, handle emergency triage
**Triggers:** Incoming call via Twilio/VAPI
**Tools:** VAPI.ai (free tier), Gemini, Firestore
**n8n Flow:** Call → VAPI handles voice → Transcribe → Gemini responds → Log conversation

---

### AGENT 5: EMERGENCY AGENT (AlertBot)
**Job:** Detect emergency keywords in any channel, alert doctor immediately
**Triggers:** Any incoming message/call with emergency signals
**Tools:** Twilio SMS, WhatsApp, Email
**n8n Flow:** All messages pass through → Gemini classifies urgency → If emergency → SMS doctor instantly

---

### AGENT 6: ONBOARDING AGENT (WelcomeBot)
**Job:** When doctor signs up, guide them through setup, collect clinic info, set up their profile
**Triggers:** New user signup in Firebase
**Tools:** Firebase, Gmail, n8n workflow
**n8n Flow:** New signup webhook → Send welcome email → Collect clinic details via form → Auto-configure their workspace

---

## 🗄️ UNIFIED INBOX DATA SCHEMA (Firestore)

```
clinics/{clinicId}/
  ├── profile/
  │   ├── doctorName, clinicName, phone, email
  │   ├── specialty (health/dental)
  │   └── settings (working hours, services, fees)
  │
  ├── patients/{patientId}/
  │   ├── name, phone, email, age
  │   └── medicalNotes
  │
  ├── appointments/{appointmentId}/
  │   ├── patientId, date, time, type
  │   ├── status (booked/confirmed/cancelled/completed)
  │   └── remindersSent[]
  │
  └── conversations/{conversationId}/
      ├── channel (whatsapp/instagram/twitter/call/email)
      ├── patientPhone/patientId
      ├── timestamp
      ├── direction (inbound/outbound)
      ├── content (text/transcript)
      ├── agentHandled (reception/social/emergency)
      └── status (open/resolved)
```

---

## 🔗 n8n MASTER ORCHESTRATOR FLOW

```
ALL_INCOMING_MESSAGES
        │
        ▼
┌───────────────────┐
│  Classify Intent  │◄── Gemini Prompt: "Classify this message: 
│  (Gemini Node)    │    appointment/emergency/query/social/unknown"
└────────┬──────────┘
         │
    ┌────┴─────┐
    │  Switch  │
    └────┬─────┘
         ├── appointment → RECEPTION AGENT flow
         ├── emergency   → EMERGENCY AGENT flow  
         ├── query       → RECEPTION AGENT flow
         ├── social      → SOCIAL MEDIA AGENT flow
         └── unknown     → Default FAQ reply
         
ALL_FLOWS → Log to Firestore conversations collection
```

---

## 🌐 WEB APP PAGES

1. **/** — Landing page (for you to sell to doctors)
2. **/signup** — Doctor onboarding form
3. **/login** — Firebase auth login
4. **/dashboard** — Main: stats, recent conversations, alerts
5. **/calendar** — Appointments view (Google Calendar embed)
6. **/inbox** — All conversations (WhatsApp, IG, calls, Twitter) in one feed
7. **/patients** — Patient directory
8. **/settings** — Clinic profile, API keys, working hours

---

## 📋 BUILD ORDER (Agent by Agent)

```
WEEK 1: Foundation
  ✅ Step 1: Web App (Login + Dashboard skeleton)
  ✅ Step 2: Firebase setup + Firestore schema
  ✅ Step 3: n8n self-hosted setup + Master Orchestrator

WEEK 2: Core Agents  
  ✅ Step 4: RECEPTION AGENT (WhatsApp + Calendar)
  ✅ Step 5: REMINDER AGENT (Cron + WhatsApp)

WEEK 3: Growth Agents
  ✅ Step 6: SOCIAL MEDIA AGENT (IG + Twitter posts)
  ✅ Step 7: CALL AGENT (VAPI.ai integration)

WEEK 4: Polish
  ✅ Step 8: EMERGENCY AGENT
  ✅ Step 9: ONBOARDING AGENT
  ✅ Step 10: Unified Inbox Dashboard complete
```

---

## 🔮 GOOGLE GEMINI PROMPTS (Master Prompts)

### Master Classifier Prompt (used in n8n)
```
You are ClinicOS, an AI assistant for a medical clinic in India.

A message has arrived from channel: {{channel}}
Message: {{message}}
Sender: {{sender_phone}}
Clinic: {{clinic_name}} ({{specialty}})

Classify the intent as ONE of:
- APPOINTMENT_BOOK: wants to book/schedule
- APPOINTMENT_RESCHEDULE: wants to change timing  
- APPOINTMENT_CANCEL: wants to cancel
- EMERGENCY: medical emergency, urgent, chest pain, accident, bleeding
- GENERAL_QUERY: asking about services, fees, timing, location
- SOCIAL_REPLY: comment/DM on social media
- FOLLOWUP: post-visit question
- UNKNOWN: cannot determine

Respond ONLY with JSON:
{"intent": "APPOINTMENT_BOOK", "confidence": 0.95, "language": "hindi/english/hinglish"}
```

### Reception Agent Prompt
```
You are ReceptBot, the AI receptionist for {{clinic_name}} in India.
Doctor: Dr. {{doctor_name}} | Specialty: {{specialty}}
Working hours: {{working_hours}}
Services: {{services_list}}
Fees: {{fees}}

Patient message: {{message}}
Intent: {{classified_intent}}
Patient history: {{patient_history_if_any}}
Available slots: {{available_slots}}

Your job:
1. Reply warmly in the same language as patient (Hindi/English/Hinglish)
2. If booking — confirm slot, collect name+age+phone if new patient
3. If query — answer from clinic info above
4. Keep replies SHORT (WhatsApp style, under 100 words)
5. Always end with a helpful next step

Respond with JSON:
{
  "reply": "message to send patient",
  "action": "book_appointment / send_info / escalate_to_doctor / none",
  "appointment_details": {} // if booking
}
```

### Social Media Content Prompt
```
You are BuzzBot, social media manager for {{clinic_name}}, a {{specialty}} clinic in {{city}}, India.

Generate a {{post_type}} post for {{platform}} (Instagram/Twitter).
Topic: {{topic}} (e.g., "dental hygiene tips", "monsoon health", "teeth whitening offer")
Tone: Friendly, trustworthy, local Indian audience
Include: relevant emojis, 3-5 hashtags in Hindi+English
Doctor name: Dr. {{doctor_name}}

Rules:
- Instagram: 150-200 words, story-style
- Twitter/X: under 250 chars, punchy
- NEVER make false medical claims
- Include a soft CTA: "Book your appointment: {{whatsapp_link}}"

Return JSON: {"caption": "...", "hashtags": [...], "suggested_image_prompt": "..."}
```

### Emergency Detection Prompt
```
You are AlertBot, emergency detector for a medical clinic.

Analyze this message for emergency signals:
Message: {{message}}
Channel: {{channel}}

Emergency signals: chest pain, heart attack, difficulty breathing, 
unconscious, accident, heavy bleeding, stroke, seizure, severe pain,
"doctor immediately", "emergency", "ambulance", critical

Respond with JSON:
{
  "is_emergency": true/false,
  "urgency_level": "critical/high/medium/low",
  "emergency_type": "cardiac/respiratory/trauma/other/none",
  "suggested_action": "call_doctor_immediately / send_emergency_info / normal_flow",
  "patient_message": "Reassuring message to send patient in their language"
}
```

---

## 🛠️ n8n WORKFLOWS TO BUILD (Step by Step)

### Workflow 1: WhatsApp Incoming Handler
```
Webhook (POST /whatsapp-incoming)
  → Set Variables (clinicId, message, sender)
  → HTTP Request (Gemini API - classify intent)
  → Switch (by intent)
    → Case APPOINTMENT: 
        → Firestore (get available slots)
        → HTTP Request (Gemini - reception reply)
        → Twilio (send WhatsApp reply)
        → Firestore (log conversation + create appointment)
    → Case EMERGENCY:
        → HTTP Request (Gemini - emergency response)
        → Twilio (SMS doctor)
        → Twilio (send patient emergency info)
        → Firestore (log as URGENT)
    → Case QUERY:
        → HTTP Request (Gemini - answer query)
        → Twilio (send reply)
        → Firestore (log)
```

### Workflow 2: Daily Reminders
```
Cron (every hour, 8am-8pm)
  → Firestore (query: appointments in next 24hrs + 2hrs)
  → Loop for each appointment:
      → Twilio (send WhatsApp reminder)
      → Firestore (update: reminder_sent = true)
```

### Workflow 3: Social Media Scheduler
```
Cron (Mon/Wed/Fri 10am)
  → Firestore (get clinic profile + topic queue)
  → HTTP Request (Gemini - generate post)
  → IF Instagram:
      → Meta Graph API (post to IG)
  → IF Twitter:
      → Twitter API v2 (post tweet)
  → Firestore (log post)
```

---

## 💡 GOOGLE AISTUDIO / ANTIGRAVITY BUILD PROMPTS

### Prompt to build the Web App
```
Build a complete single-page web application for "ClinicOS" - an AI-powered clinic management platform for Indian doctors.

Tech stack: HTML, CSS, JavaScript, Firebase (Auth + Firestore)

Pages to build:
1. Login/Signup page with Firebase auth
2. Dashboard: Shows today's appointments count, unread messages, recent conversations feed, quick stats
3. Calendar view: Shows appointments in monthly/weekly view
4. Inbox: Shows all conversations from WhatsApp/Instagram/Twitter/Calls in one unified feed with channel icons
5. Patients page: List of patients with search
6. Settings: Clinic profile form

Design: Clean, medical/professional, teal and white color scheme, mobile-responsive

Firebase config: Use environment variables
Each conversation card in inbox should show: channel icon, patient name, time, last message preview, status badge (open/resolved/urgent)
```

### Prompt to build Reception Agent in Python
```
Build a Python Flask API that acts as an AI receptionist for medical clinics.

Endpoint: POST /reception
Input: {message, sender_phone, clinic_id, channel}

Steps:
1. Load clinic profile from Firestore (using clinic_id)
2. Load patient history if phone exists in DB
3. Call Google Gemini 1.5 Flash API to classify intent
4. Based on intent, call appropriate sub-function:
   - book_appointment(): Query Google Calendar for free slots, create event
   - answer_query(): Use clinic profile data to answer
   - escalate(): Flag for doctor review
5. Log conversation to Firestore (conversations collection)
6. Return: {reply_message, action_taken, appointment_id}

Use: google-generativeai, firebase-admin, google-calendar-api Python libraries
Include error handling and logging
```

---

## 📱 WHATSAPP SETUP (Free via Twilio Sandbox)
1. Create Twilio account (free $15 credit)
2. Enable WhatsApp Sandbox
3. Sandbox number shared for testing
4. Set webhook: your n8n URL + /whatsapp-incoming
5. For production: Apply for Twilio WhatsApp Business API (₹0 for first 1000 conversations/month via Meta)

## 📞 CALL SETUP (Free via VAPI.ai)
1. Create VAPI.ai account (free tier: 10 hours/month)
2. Create an assistant with your Gemini prompt
3. Get phone number (or use web calling)
4. Set post-call webhook to n8n for logging

---

## 🚀 GO-TO-MARKET: Getting First 10 Clinics

1. **Target:** Standalone dental/health clinics in Tier-2 cities (Pune, Jaipur, Lucknow, Mysuru)
2. **Pitch:** "Replace your ₹15,000/month receptionist with ₹4,999/month AI"
3. **Demo:** Show live WhatsApp booking in their own number
4. **Onboard:** 30-minute setup, we handle everything
5. **Referral:** ₹2,000 credit for every clinic they refer

---

## 📊 PATH TO ₹1 CRORE/MONTH

| Milestone | Clinics | MRR |
|-----------|---------|-----|
| Month 3 | 20 | ₹1L |
| Month 6 | 100 | ₹5L |
| Month 12 | 500 | ₹25L |
| Month 18 | 2000 | ₹1Cr |

**Each agent you build reduces your cost and increases your margin.**

---

*Next Step: Start with Agent 1 (Reception Agent) — share this doc with your AI builder and use the prompts above.*
