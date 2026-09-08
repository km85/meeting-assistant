# Meeting Assistant - MVP Architecture Document

## Overview

A privacy-first meeting assistant that captures audio from Android, transcribes via STT APIs, processes with AI APIs, and delivers insights via Telegram bot. BYOK (Bring Your Own Key) model. Local-first data storage.

**MVP Scope:**
- Android app (audio capture + UI)
- Telegram Bot (commands + output)
- Deepgram STT (primary)
- OpenAI GPT-4o-mini (primary)
- 1 Mode: General Meeting (summary + action items)
- 1 Knowledge Base per user
- 7-day free trial, then $50 lifetime license
- Direct website distribution (no Play Store)

**Out of MVP:**
- Web app (v1.1)
- Additional modes (v1.2 DLC)
- VPS sync (v1.2 DLC)
- A la carte features (v1.2+)
- Multiple STT providers (v1.1)
- Bluetooth mic optimization (v1.1)

---

## Target Users

**Primary Persona:**
- Corporate employee who cannot install software on company laptop
- Uses personal Android phone for audio capture
- Reviews output via Telegram Web on company laptop
- Privacy-conscious, doesn't want meeting data on company/cloud servers
- Willing to bring their own API keys (Deepgram, OpenAI)

**Use Cases:**

### UC1: Start Meeting Session
1. User opens Android app
2. Selects project/knowledge base (or "default")
3. Taps "Start Meeting"
4. App starts background recording + streams audio to Deepgram
5. Telegram bot sends: "Meeting started. Use /assist for help, /stop to end."

### UC2: Real-time Assistance
1. User hears question in meeting they don't know how to answer
2. User opens Telegram, types: `/assist How should I respond to budget concerns?`
3. Bot sends context + question to OpenAI with knowledge base context
4. Bot replies with suggested answer (2-3 bullet points)

### UC3: Ask to Speak
1. User wants to contribute but doesn't know what to say
2. User types: `/say Latest project update`
3. Bot generates speaking points based on knowledge base + meeting context
4. Bot replies with draft statement

### UC4: Meeting Recap
1. User types: `/recap`
2. Bot sends transcript summary + action items + key decisions
3. Bot offers: `/followup` for suggested questions

### UC5: End Session
1. User types: `/stop` or taps "Stop" in app
2. Bot sends final summary + transcript file
3. App saves transcript to local storage
4. Session ends

### UC6: Setup (First Time)
1. User installs APK from website
2. Opens app, enters license key (or starts 7-day trial)
3. Enters API keys: Deepgram, OpenAI, Telegram Bot Token
4. App validates all keys (test API calls)
5. User creates first project/knowledge base
6. Done

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER PHONE                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Android App   │  │ Telegram     │  │ Local Storage        │  │
│  │ (Audio + UI)  │  │ Client       │  │ (SQLite)             │  │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────────┘
          │                │
          │ Audio Stream   │ Text/Commands
          ▼                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     EXTERNAL APIs                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ Deepgram      │  │ OpenAI       │  │ Telegram Bot API     │  │
│  │ (STT)         │  │ (LLM)        │  │ (Send/Receive)       │  │
│  └──────────────┘  └──────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Breakdown

### 1. Android App (Flutter - MVP)

**Why Flutter for MVP:**
- Faster development (single codebase, hot reload)
- Can add iOS later without rewrite
- Rich UI libraries
- If audio doesn't work well, we pivot to Kotlin early (week 1-2)

**Risk:** Flutter background audio + real-time streaming is harder than Kotlin. If blocked, switch to Kotlin.

**Modules:**

```
android_app/
├── lib/
│   ├── main.dart                 # App entry
│   ├── screens/
│   │   ├── home_screen.dart      # Main screen (start/stop)
│   │   ├── setup_screen.dart     # API key setup
│   │   ├── settings_screen.dart  # License, config
│   │   └── project_screen.dart   # Knowledge base editor
│   ├── services/
│   │   ├── audio_service.dart    # Background recording + stream
│   │   ├── deepgram_service.dart # STT API client
│   │   ├── openai_service.dart   # LLM API client
│   │   ├── telegram_service.dart # Bot API client
│   │   ├── storage_service.dart  # SQLite wrapper
│   │   └── license_service.dart  # Trial + license validation
│   └── models/
│       ├── session.dart          # Meeting session data
│       ├── transcript.dart       # Transcript chunk
│       ├── project.dart          # Knowledge base
│       └── config.dart           # User settings
```

**Key Technical Details:**

**Audio Service:**
- Uses `flutter_sound` or `record` plugin
- Foreground service (persistent notification: "Recording meeting...")
- Audio format: 16kHz, mono, 16-bit PCM (Deepgram optimal)
- Buffer size: 100-200ms chunks for real-time streaming
- Permissions: RECORD_AUDIO, FOREGROUND_SERVICE, WAKE_LOCK
- Battery optimization: request ignore in settings

**Deepgram Integration:**
- WebSocket connection (real-time streaming)
- Endpoint: `wss://api.deepgram.com/v1/listen`
- Parameters: `model=nova-2`, `language=multilingual`, `punctuate=true`
- Interim results: true (show live transcript)
- Final results: every 2-3 seconds
- Keep-alive during silence

**OpenAI Integration:**
- HTTP POST to `https://api.openai.com/v1/chat/completions`
- Model: `gpt-4o-mini` (fast, cheap, good enough)
- System prompt: loaded from `meeting_mode` config (default meeting mode)
- Context window: last 10 transcript chunks + knowledge base
- Max tokens: 500 (concise responses)

**Telegram Integration:**
- Bot API: `https://api.telegram.org/bot<TOKEN>/sendMessage`
- Webhook or polling: Long polling for MVP (simpler)
- Bot handles commands: `/assist`, `/say`, `/recap`, `/stop`, `/status`
- User identifies themselves via chat ID (linked in app)

**Storage (SQLite):**
```sql
-- Projects / Knowledge Base
CREATE TABLE projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    context TEXT,          -- Injected into prompts
    created_at TIMESTAMP
);

-- Sessions
CREATE TABLE sessions (
    id INTEGER PRIMARY KEY,
    project_id INTEGER,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    status TEXT,           -- active, completed, error
    telegram_chat_id TEXT,
    deepgram_session_id TEXT
);

-- Transcript chunks
CREATE TABLE transcript_chunks (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    speaker TEXT,          -- "Speaker 1", "Speaker 2", etc.
    text TEXT NOT NULL,
    timestamp REAL,        -- seconds from start
    is_final BOOLEAN,      -- true = final, false = interim
    created_at TIMESTAMP
);

-- App config
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- Keys: deepgram_api_key, openai_api_key, telegram_bot_token, 
--       license_key, trial_start_date, telegram_chat_id
```

**License/Trial Logic:**
```
On first open:
  - Check if license_key exists
  - If not: start trial (store trial_start_date = now)
  - Trial lasts 7 days from trial_start_date
  - After 7 days: show paywall (enter license key or purchase)
  - License key validated against server (simple API: POST /verify {key, device_id})
```

---

### 2. Telegram Bot

**Bot Commands:**

```
/assist <question>  - Ask for help with a meeting situation
/say <topic>        - Generate speaking points on a topic  
/recap              - Summarize meeting so far
/followup           - Suggest follow-up questions
/stop               - End meeting session
/status             - Check if recording is active
/projects           - List knowledge bases
/use_project <name> - Switch active knowledge base
```

**Bot Flow:**

```
User sends /assist "How do we handle the delay?"
  ↓
Bot checks: is there an active session for this chat_id?
  ↓ No → "No active meeting. Start one in the app first."
  ↓ Yes → 
Bot fetches: last 10 transcript chunks + project context
  ↓
Bot builds prompt:
  "You are a meeting assistant. Context: [project]. 
   Recent meeting transcript: [last 10 chunks].
   User needs help: How do we handle the delay?
   Give concise, actionable advice (2-3 bullets)."
  ↓
Bot calls OpenAI API
  ↓
Bot sends response to user (formatted, 2-3 bullet points)
```

**Implementation:**
- Long polling: every 30 seconds, check for new messages
- When message received: parse command, execute, respond
- Bot runs as part of Android app (background service) OR separate backend
- **MVP decision:** Bot runs as part of Android app (no separate backend needed)
  - User provides bot token
  - App registers webhook or starts polling service
  - Commands processed locally on phone

---

### 3. Data Flow (Sequence Diagrams)

#### Flow 1: Start Meeting

```
User (App)          Android App          Deepgram          Telegram Bot          OpenAI
   |                      |                   |                      |                  |
   |-- Tap Start -------->|                   |                      |                  |
   |                      |-- Init WS ------>|                      |                  |
   |                      |<-- Connected ----|                      |                  |
   |                      |                   |                      |                  |
   |                      |-- Start Foreground Service              |                  |
   |                      |-- Start Recording                       |                  |
   |                      |                   |                      |                  |
   |                      |-- Send msg: "Meeting started" -------->|                  |
   |                      |                   |                      |-- Send to User ->|
```

#### Flow 2: Real-time Transcription (Every 200ms)

```
Android App          Deepgram          (SQLite)
      |                  |                  |
      |-- Audio Chunk -->|                  |
      |                  |-- Process        |
      |<-- Interim ----|                  |
      |-- Store interim |                  |
      |                  |                  |
      |-- Audio Chunk -->|                  |
      |                  |                  |
      |<-- Final -------|                  |
      |-- Store final --|                  |
```

#### Flow 3: User Asks /assist

```
User (Telegram)       Telegram Bot          Android App          SQLite          OpenAI
      |                      |                   |                  |               |
      |-- /assist "How do    |                   |                  |               |
      |    we handle delay?"|                   |                  |               |
      |                      |                   |                  |               |
      |                      |<-- Receive cmd --|                  |               |
      |                      |                   |                  |               |
      |                      |-- Fetch last 10 chunks + context -->|               |
      |                      |<-- Return data ---|                  |               |
      |                      |                   |                  |               |
      |                      |-- Build prompt, call OpenAI ------>|               |
      |                      |<-- Response ----|                  |               |
      |                      |                   |                  |               |
      |<-- Send response ----|                   |                  |               |
```

#### Flow 4: End Meeting (/stop)

```
User (Telegram)       Telegram Bot          Android App          Deepgram          SQLite
      |                      |                   |                  |               |
      |-- /stop ------------>|                   |                  |               |
      |                      |<-- Receive cmd ---|                  |               |
      |                      |                   |                  |               |
      |                      |-- Tell app: stop -|                  |               |
      |                      |                   |                  |               |
      |                      |                   |-- Close WS ---->|               |
      |                      |                   |<-- Closed ------|               |
      |                      |                   |                  |               |
      |                      |                   |-- Stop recording |               |
      |                      |                   |-- Mark session   |               |
      |                      |                   |   completed      |               |
      |                      |                   |                  |               |
      |                      |-- Fetch full summary ---------------->|               |
      |                      |<-- Return data ---|                  |               |
      |                      |                   |                  |               |
      |<-- Send summary -----|                   |                  |               |
```

---

### 4. Website (Landing Page + Payment)

**Stack:** Static HTML + Stripe Checkout (simplest)

**Pages:**
1. **Landing Page** (`/`)
   - Hero: "Your meetings, your data, your AI"
   - Features: Privacy-first, BYOK, lifetime access
   - How it works: 3 steps diagram
   - Pricing: $50 lifetime, 7-day trial
   - FAQ: What APIs do I need? How does it work? Is it legal?

2. **Purchase Page** (`/buy`)
   - Stripe Checkout integration
   - After payment: generate license key, show on screen + email
   - Download APK link

3. **Download Page** (`/download`)
   - APK download link
   - Setup instructions (API key links, Telegram bot setup)
   - Video tutorial (placeholder for now)

**License Validation API (Backend):**
```
POST /api/verify-license
Request: { license_key, device_id }
Response: { valid: true/false, message: "..." }

POST /api/activate-license
Request: { license_key, device_id }
Response: { activated: true/false, message: "..." }
```

**Backend:** FastAPI (Python) or simple Node.js/Express
- SQLite database: licenses (key, email, purchase_date, status)
- Deploy: VPS or even serverless (Vercel/Netlify functions + Neon DB)

---

### 5. API Key Setup (Revenue Channel Foundation)

**MVP: Manual input only**

App has fields for:
- Deepgram API Key (link to deepgram.com with affiliate/ref if possible)
- OpenAI API Key (link to platform.openai.com)
- Telegram Bot Token (link to @BotFather instructions)

**Post-MVP: Assisted Setup**
- Deep links to provider signup pages with referral parameters
- In-app cost estimator: "Deepgram ~$0.43/hour, OpenAI ~$0.50/hour"
- "Get $10 free credits" links (affiliate)

**Why not in MVP:** Scope creep. Affiliate/referral deals take time to negotiate. Build product first, monetize channels later.

---

### 6. Audio Quality Strategy (MVP)

**Default:** Phone microphone, direct recording

**Optimizations (MVP):**
1. Audio preprocessing before sending to Deepgram:
   - Gain normalization (boost quiet audio)
   - High-pass filter (remove low-frequency rumble)
   - Noise gate (mute below threshold)

2. User guidance (in-app + onboarding):
   - "Place phone on table, 0.5-1 meter from you"
   - "Do not put in pocket during meeting"
   - "Face microphone toward speakers"
   - "Use in quiet rooms when possible"

3. Quality indicator:
   - Show audio level meter in app
   - Green = good, Yellow = okay, Red = too quiet/noisy
   - If red for 10 seconds, show warning: "Audio may be unclear. Move phone closer?"

**Post-MVP:**
- Bluetooth mic support (better audio from earbuds)
- Speaker diarization (identify who is speaking)
- Room calibration (test audio in current room)

---

## Security & Privacy

**Data Handling:**
- All meeting data stored locally on phone (SQLite)
- Transcripts never sent to our servers (only to user's own API keys)
- API keys stored in Android Keystore (encrypted, not plain text)
- No telemetry/analytics in MVP (add later, opt-in only)
- Network: HTTPS/WSS for all API calls (standard)

**User Control:**
- User can delete all data anytime (clear app data)
- User can export transcripts (JSON/CSV)
- User can change API keys anytime
- No account creation required

**What We DON'T Collect:**
- No meeting content on our servers
- No audio recordings (only live stream, not stored)
- No user email (unless they provide for purchase receipt)
- No usage analytics (MVP)

---

## Development Roadmap (MVP: 3-4 Weeks)

### Week 1: Audio Capture + Deepgram
- [ ] Flutter project setup
- [ ] Audio permissions + foreground service
- [ ] Audio recording (PCM 16kHz mono)
- [ ] Deepgram WebSocket integration
- [ ] Live transcript display in app
- [ ] Audio quality test (record in real room, check accuracy)
- [ ] **GO/NO-GO decision:** If audio accuracy <70% from 2 meters, pivot to Kotlin or add Bluetooth mic requirement

### Week 2: OpenAI + Telegram
- [ ] OpenAI API integration (GPT-4o-mini)
- [ ] Prompt engineering for meeting mode
- [ ] Telegram bot setup (polling)
- [ ] Command handlers: /assist, /say, /recap, /stop
- [ ] Knowledge base injection (project context)
- [ ] SQLite database setup
- [ ] End-to-end test: record → transcribe → process → Telegram output

### Week 3: UI + License + Polish
- [ ] App UI: Home, Setup, Settings, Projects
- [ ] License validation API (backend)
- [ ] Trial logic (7-day countdown)
- [ ] APK build + signing
- [ ] Onboarding flow (first-time setup wizard)
- [ ] Error handling (API failures, network issues)
- [ ] Battery optimization

### Week 4: Website + Launch Prep
- [ ] Landing page (HTML + Stripe)
- [ ] License purchase flow
- [ ] APK download page
- [ ] Basic documentation (setup guide, FAQ)
- [ ] Beta testing (5-10 users)
- [ ] Fix critical bugs
- [ ] Launch to public

---

## Success Criteria (MVP Launch)

1. **Audio Quality:** Deepgram accuracy >70% from 2 meters in average meeting room
2. **Latency:** User gets Telegram response within 5 seconds of sending /assist
3. **Stability:** App runs for 1-hour meeting without crash or disconnect
4. **Usability:** User can set up app in <10 minutes (including API key signup)
5. **Privacy:** Zero data on our servers, all local

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Audio quality too poor | High | Critical | Test in Week 1, pivot to Kotlin if needed, add Bluetooth mic support |
| Flutter background audio unreliable | Medium | High | Use foreground service, test extensively, have Kotlin fallback plan |
| Telegram Bot API rate limits | Low | Medium | Add retry logic, use exponential backoff |
| User API key billing shock | Medium | Medium | In-app cost estimator, spending warnings, clear onboarding |
| License key piracy | Medium | Low | Device binding, simple online validation, don't over-engineer |
| Play Store not used (sideload) | N/A | Low | Clear install guide, handle APK security warnings, consider F-Droid later |

---

## Post-MVP Roadmap (Not Now, But Documented)

**v1.1 (Month 2-3):**
- Web app (review transcripts, manage projects)
- Multiple STT providers (AssemblyAI, Whisper API as fallback)
- Bluetooth microphone support
- Affiliate links for API providers (revenue channel)

**v1.2 (Month 3-4):**
- DLC Modes: Interview ($10), Presentation ($10)
- A la carte: Custom output format ($5), Advanced analytics ($5)
- VPS sync feature ($5 DLC)
- Multiple knowledge bases

**v1.3 (Month 4-6):**
- iOS app (if Flutter MVP works well)
- Team/Enterprise features
- Web dashboard
- Advanced: Speaker diarization, sentiment analysis

---

## Open Questions

1. **Flutter vs Kotlin:** Will Flutter audio plugins work for our use case? Decision by end of Week 1.
2. **Telegram bot hosting:** Run in Android app or separate backend? MVP = in app, but might need backend for reliability.
3. **License validation:** Simple server or fully offline? Offline = piracy risk, server = infrastructure cost. Propose: lightweight serverless validation.
4. **Transcript storage:** Keep all history or auto-delete after 30 days? Propose: keep until user deletes, storage is local.

---

## Document Version
- **Version:** 1.0
- **Date:** 2026-06-08
- **Status:** Draft for review
- **Author:** kris_claw (AI assistant) for Krishna Malik

---

*Next Step: Review and approve this architecture. Then proceed to Week 1: Audio Test App.*
