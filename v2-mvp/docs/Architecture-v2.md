# Meeting Assistant - v2 MVP Architecture

## Overview

**Version:** 2.0-MVP  
**Architecture:** Direct-to-API (no backend)  
**Platform:** Android (Kotlin native)  
**Date:** 2026-06-08

A privacy-first meeting assistant that runs entirely on the user's phone. No backend server needed. User brings their own API keys (BYOK).

**MVP Scope:**
- Android Kotlin app (audio capture + UI + API clients + Telegram bot)
- Direct connection to Deepgram (STT) and OpenAI (LLM)
- Telegram bot runs inside the app (background polling)
- 1 Mode: General Meeting (summary + action items)
- 1 Knowledge Base per user
- 7-day free trial, then $50 lifetime license
- Direct website distribution (no Play Store)

**Eliminated from v1:**
- ❌ Backend server (FastAPI)
- ❌ Docker containers
- ❌ VPS requirement
- ❌ WebSocket relay through backend
- ❌ In-memory session storage (replaced with SQLite)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER PHONE                                  │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │                    Android App (Kotlin)                       │   │
│  │                                                              │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │   │
│  │  │ Audio Service│  │ API Clients  │  │ Telegram Bot     │  │   │
│  │  │ (Foreground) │  │              │  │ (Background)     │  │   │
│  │  │              │  │ • Deepgram   │  │                  │  │   │
│  │  │ • Record     │  │   (WebSocket)│  │ • Poll /getUpdates│  │   │
│  │  │ • PCM 16kHz  │  │ • OpenAI     │  │ • Handle commands │  │   │
│  │  │ • Stream     │  │   (HTTP)     │  │ • Send responses  │  │   │
│  │  │              │  │              │  │                  │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │   │
│  │         │                 │                    │            │   │
│  │  ┌──────┴─────────────────┴────────────────────┴─────────┐  │   │
│  │  │                   SQLite Local Storage                   │  │   │
│  │  │  • Transcript chunks  • API keys (encrypted)          │  │   │
│  │  │  • Session data        • License status                 │  │   │
│  │  │  • Projects/KB        • Settings                      │  │   │
│  │  └───────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Deepgram API   │ │  OpenAI API     │ │ Telegram Bot API│
│  (WebSocket)    │ │  (HTTP)         │ │  (HTTP Polling) │
│                 │ │                 │ │                 │
│  • Real-time STT│ │  • GPT-4o-mini  │ │  • /assist      │
│  • Nova-2 model │ │  • GPT-5.5      │ │  • /say         │
│  • Multilingual │ │  • Fast/Deep    │ │  • /recap       │
│                 │ │                 │ │  • /stop        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## Key Technical Decisions

### 1. No Backend (Direct-to-API)

**Why:**
- User controls all data (nothing on our servers)
- No infrastructure cost for us
- Simpler architecture
- Faster to build

**How it works:**
- Android app opens WebSocket directly to `wss://api.deepgram.com/v1/listen`
- Android app sends HTTPS POST directly to `https://api.openai.com/v1/chat/completions`
- Android app polls Telegram API directly for bot commands

### 2. Kotlin Native (Not Flutter)

**Why:**
- v1-sprint1 proved Kotlin audio works
- Better audio API access (foreground service, AudioRecord)
- Reuse 60% of existing v1 Android code
- Native performance for real-time audio

**Risk:** Slower to add iOS later (need separate Swift project)
**Mitigation:** iOS is v1.4, not MVP. Focus on Android first.

### 3. Telegram Bot in App (Not Backend)

**Why:**
- No backend needed
- User creates their own bot via @BotFather
- User provides bot token to app
- App polls Telegram in background service

**Limitation:**
- Bot only works when app is running
- During meeting, app IS running (foreground service for audio)
- After meeting, app may be killed by OS → bot stops
- Post-MVP: add serverless bot as optional

**MVP workaround:**
- App sends notifications via Telegram (always works via API)
- Commands can be sent from app UI if bot is offline
- Bot is primarily for convenience during active meeting

### 4. SQLite Local Storage

**Why:**
- All data stays on phone
- No cloud dependency
- Simple, fast, reliable
- User can export/delete anytime

**Schema:**
```sql
-- App config (API keys, license, settings)
CREATE TABLE config (
    key TEXT PRIMARY KEY,
    value TEXT
);
-- Keys: deepgram_api_key, openai_api_key, telegram_bot_token, 
--       license_key, trial_start_date, telegram_chat_id

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
    FOREIGN KEY (project_id) REFERENCES projects(id)
);

-- Transcript chunks
CREATE TABLE transcript_chunks (
    id INTEGER PRIMARY KEY,
    session_id INTEGER,
    speaker TEXT,
    text TEXT NOT NULL,
    timestamp REAL,        -- seconds from session start
    is_final BOOLEAN,
    created_at TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

---

## Component Breakdown

### 1. Audio Service (Foreground)

**Reused from v1:** `MeetingService.kt` (heavily modified)

**Changes:**
- Remove `WebSocketClient` (backend connection)
- Add `DeepgramClient` (direct WebSocket to Deepgram)
- Keep: `AudioRecord`, foreground notification, recording loop
- Add: audio preprocessing (gain normalization, noise gate)

**New: DeepgramClient.kt**
```kotlin
class DeepgramClient(private val apiKey: String) {
    private val wsUrl = "wss://api.deepgram.com/v1/listen?model=nova-2&language=multilingual&punctuate=true&interim_results=true&encoding=linear16&sample_rate=16000&channels=1"
    
    // Connect with Authorization header
    // Send audio chunks as binary
    // Receive transcript JSON
    // Store in SQLite
    // Auto-reconnect on disconnect
}
```

### 2. OpenAI Client

**New component:** `OpenAIClient.kt`

```kotlin
class OpenAIClient(private val apiKey: String) {
    private val baseUrl = "https://api.openai.com/v1/chat/completions"
    
    suspend fun generateResponse(
        prompt: String,
        model: String = "gpt-4o-mini",
        maxTokens: Int = 500
    ): String {
        // POST to OpenAI
        // Parse response
        // Return text
    }
}
```

**Dual model approach (from v1):**
- `/assist`, `/say` → `gpt-4o-mini` (fast, real-time)
- `/recap`, `/followup` → `gpt-5.5` (deep analysis)

### 3. Telegram Bot Service (Background)

**New component:** `TelegramBotService.kt`

```kotlin
class TelegramBotService(private val botToken: String) {
    private val baseUrl = "https://api.telegram.org/bot$botToken"
    private var lastUpdateId: Long = 0
    
    // Polling loop (every 5 seconds)
    // Parse commands: /assist, /say, /recap, /stop, /status
    // For each command:
    //   1. Fetch recent transcript from SQLite
    //   2. Build prompt (inject project context)
    //   3. Call OpenAIClient
    //   4. Send response via Telegram API
    //   5. Log latency
}
```

**Runs as:** Bound service to MeetingService (or separate background service). Only active during meeting session.

### 4. Storage (SQLite)

**New component:** `DatabaseHelper.kt` (Room or raw SQLite)

```kotlin
class DatabaseHelper(context: Context) : SQLiteOpenHelper(context, "meeting_assistant.db", null, 1) {
    // CRUD for: config, projects, sessions, transcript_chunks
    // Export transcript to file
    // Clear old data
}
```

**Use Room (Jetpack) for cleaner API:**
```kotlin
@Entity(tableName = "config")
data class ConfigEntry(
    @PrimaryKey val key: String,
    val value: String
)

@Entity(tableName = "transcript_chunks")
data class TranscriptChunk(
    @PrimaryKey(autoGenerate = true) val id: Int = 0,
    val sessionId: Int,
    val speaker: String?,
    val text: String,
    val timestamp: Float,
    val isFinal: Boolean,
    val createdAt: Long = System.currentTimeMillis()
)
```

### 5. UI (Activities)

**HomeActivity** (main screen)
- Start/Stop meeting button
- Audio level indicator (green/yellow/red)
- Current session status
- Active project display
- Quick commands: /assist, /say, /recap (as buttons)

**SetupActivity** (first-time + settings)
- Deepgram API key input
- OpenAI API key input
- Telegram bot token input
- Test connections button (validate each API)
- License key input (or start trial)

**ProjectsActivity** (knowledge base)
- List projects
- Add/edit project (name, description, context)
- Set active project
- Delete project

**SettingsActivity**
- License status (trial countdown or lifetime)
- Storage usage (transcript size, clear data)
- Export transcripts
- About / help

---

## Data Flow (Sequence Diagrams)

### Flow 1: Start Meeting

```
User (HomeActivity)      AudioService          DeepgramClient        SQLite
        |                      |                       |                  |
        |-- Tap Start -------->|                       |                  |
        |                      |-- Start Foreground    |                  |
        |                      |-- Start Recording     |                  |
        |                      |-- Init Deepgram WS ->|                  |
        |                      |                      |-- Connect        |
        |                      |                      |-- Auth header    |
        |                      |<-- Connected --------|                  |
        |                      |                       |                  |
        |                      |-- Send metadata      |                  |
        |                      |                      |                  |
        |<-- "Listening..." ---|                       |                  |
        |                      |                       |                  |
        |-- Send Telegram msg via API --> (to user chat)
        "Meeting started. Use /assist for help, /stop to end."
```

### Flow 2: Real-time Transcription (Every 200ms)

```
AudioService          DeepgramClient          Deepgram API          SQLite
      |                       |                      |                  |
      |-- Audio chunk -------->|                      |                  |
      |                       |-- Send binary ------>|                  |
      |                       |                      |-- Process        |
      |                       |                      |                  |
      |                       |<-- Interim result --|                  |
      |                       |                      |                  |
      |                       |-- Store interim -->|                  |
      |                       |                      |                  |
      |                       |<-- Final result ----|                  |
      |                       |                      |                  |
      |                       |-- Store final ---->|                  |
      |                       |                      |                  |
      |                       |-- Log transcript   |                  |
      |                       |                      |                  |
      |                       |-- Update UI (if app visible)            |
```

### Flow 3: User Sends /assist from Telegram

```
Telegram API      TelegramBotService         SQLite          OpenAIClient      Telegram API
      |                      |                   |                  |               |
      |-- /assist msg ------>|                   |                  |               |
      |                      |                   |                  |               |
      |                      |-- Fetch recent transcript + context -->|               |
      |                      |<-- Return data --|                  |               |
      |                      |                   |                  |               |
      |                      |-- Build prompt, call OpenAI ----->|               |
      |                      |<-- Response ----|                  |               |
      |                      |                   |                  |               |
      |<-- Send response ----|                   |                  |               |
      |                      |                   |                  |               |
      |-- Deliver to user ---|                   |                  |               |
```

### Flow 4: End Meeting (/stop)

```
User (Telegram)   TelegramBotService      AudioService      DeepgramClient      SQLite
      |                      |                  |                  |                  |
      |-- /stop ------------>|                  |                  |                  |
      |                      |-- Tell AudioService to stop -->|                  |
      |                      |                  |                  |                  |
      |                      |                  |-- Stop recording |                  |
      |                      |                  |-- Close WS ---->|                  |
      |                      |                  |                  |-- Disconnect     |
      |                      |                  |                  |                  |
      |                      |                  |-- Mark session complete -->|           |
      |                      |                  |                  |                  |
      |                      |-- Fetch summary ------------------------------->|           |
      |                      |<-- Return transcript ---|                  |                  |
      |                      |                  |                  |                  |
      |                      |-- Call OpenAI (deep model) ------------------>|           |
      |                      |<-- Recap response --|                  |                  |
      |                      |                  |                  |                  |
      |<-- Send recap ------|                  |                  |                  |
```

---

## API Key Management

**Storage:** Encrypted SharedPreferences (Android Keystore optional for v1.1)

```kotlin
class SecureStorage(context: Context) {
    private val prefs = context.getSharedPreferences("secure", Context.MODE_PRIVATE)
    
    // Simple encryption with AES (sufficient for MVP)
    // Keys stored with Android Keystore for v1.1
    
    fun setApiKey(provider: String, key: String) {
        prefs.edit().putString("api_key_$provider", encrypt(key)).apply()
    }
    
    fun getApiKey(provider: String): String? {
        return decrypt(prefs.getString("api_key_$provider", null))
    }
}
```

**Validation:** Test API call on save
- Deepgram: Test WebSocket connection (3-second timeout)
- OpenAI: Test with simple "Hello" completion (3-second timeout)
- Telegram: Test with /getMe (3-second timeout)

---

## License & Trial

```kotlin
class LicenseManager(context: Context) {
    // Trial: 7 days from first open
    // After trial: require license key
    // License key validated against server (simple serverless function)
    
    fun isTrialValid(): Boolean {
        val start = prefs.getLong("trial_start", System.currentTimeMillis())
        val days = (System.currentTimeMillis() - start) / (1000 * 60 * 60 * 24)
        return days <= 7
    }
    
    fun activateLicense(key: String): Boolean {
        // POST to serverless validation endpoint
        // Returns: valid/invalid, device_id binding
        // If valid: store key, mark as activated
    }
}
```

**Serverless validation:**
```
POST https://your-site.com/api/verify-license
{ license_key: "abc-123", device_id: "sha256-of-android-id" }

Response: { valid: true, activated: true, message: "License activated" }
```

---

## Security & Privacy

**What we DON'T do:**
- ❌ No data on our servers (no backend)
- ❌ No audio storage (only live stream)
- ❌ No telemetry/analytics (MVP)
- ❌ No user tracking
- ❌ No account creation

**What we DO:**
- ✅ API keys encrypted on device
- ✅ Transcripts local-only (SQLite)
- ✅ HTTPS/WSS for all API calls
- ✅ User can export/delete all data
- ✅ Optional: export to file, delete from app settings

**User responsibility:**
- API usage billed directly to their accounts (Deepgram, OpenAI)
- They control their API keys
- They can revoke keys anytime

---

## Development Roadmap (4 Weeks)

### Week 1: Audio + Deepgram (GO/NO-GO Week)
**Goal:** Prove audio quality works from phone in real meeting

- [ ] Set up new Kotlin project in `v2-mvp/android/`
- [ ] Copy audio recording logic from v1 (reusable)
- [ ] Build DeepgramClient (direct WebSocket)
- [ ] Test audio → Deepgram → transcript accuracy
- [ ] Test in real meeting room (phone 2-3 meters away)
- [ ] **GO/NO-GO:** If accuracy <70%, pivot strategy (add Bluetooth mic requirement, or switch to closer placement)

**Deliverable:** Audio test APK that shows live transcript

### Week 2: OpenAI + Storage
**Goal:** Process transcript with AI, store locally

- [ ] Build OpenAIClient (HTTP POST)
- [ ] Build SQLite database (Room)
- [ ] Build transcript storage logic
- [ ] Build simple UI (Home, Start/Stop, transcript display)
- [ ] Test /assist command (manual trigger, not Telegram yet)
- [ ] Test with project context injection

**Deliverable:** App that can record meeting and answer /assist from UI

### Week 3: Telegram Bot + Commands
**Goal:** Full Telegram integration

- [ ] Build TelegramBotService (polling)
- [ ] Implement all commands: /assist, /say, /recap, /followup, /stop, /status
- [ ] Build Setup UI (API key input, bot token)
- [ ] Build Project UI (knowledge base management)
- [ ] End-to-end test: Telegram → app → OpenAI → Telegram response
- [ ] Test latency (target: <5 seconds)

**Deliverable:** Complete app with Telegram integration

### Week 4: License + Website + Polish
**Goal:** Launchable product

- [ ] Build license/trial system
- [ ] Build serverless validation (Vercel/Netlify function)
- [ ] Landing page (HTML + Stripe)
- [ ] APK download + signing
- [ ] Onboarding flow (first-time setup wizard)
- [ ] Error handling, battery optimization
- [ ] Beta testing (5-10 users)
- [ ] Fix critical bugs

**Deliverable:** Public launch

---

## Success Criteria

1. **Audio Quality:** Deepgram accuracy >70% from 2 meters in average meeting room
2. **Latency:** /assist response within 5 seconds of Telegram command
3. **Stability:** 1-hour meeting without crash or disconnect
4. **Setup:** User can configure app in <10 minutes (including API key signup)
5. **Privacy:** Zero data on our servers, all local

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Audio quality too poor | High | Critical | Test Week 1. If fails, require Bluetooth mic or closer placement |
| Android OS kills app | Medium | High | Foreground service + notification + battery optimization request |
| Telegram bot polling drains battery | Medium | Medium | Polling only during active session, 5-second interval |
| User API keys exposed in logs | Medium | High | Never log keys. Encrypt in storage. Clear from memory after use |
| No network during meeting | Low | Medium | Queue transcript chunks, retry when network returns |
| License server down | Low | Low | Cache validation result, allow offline for 24h after activation |
| Play Store not available | N/A | N/A | Sideloading is our distribution model (documented install process) |

---

## Post-MVP Roadmap (from Parking Lot)

**v1.1 (Month 2-3):**
- Web app (PWA for review transcripts)
- Multiple STT providers (fallback)
- Bluetooth mic optimization
- API provider affiliate links

**v1.2 (Month 3-4):**
- DLC Modes: Interview ($10), Presentation ($10)
- A la carte features
- VPS sync option ($5 DLC)
- Multiple knowledge bases

**v1.3 (Month 4-6):**
- iOS app
- Speaker diarization
- Advanced analytics
- Export formats (PDF, Notion)

---

## Version History

- **v1-sprint1** (2026-06-04): Backend relay architecture. Android → VPS → Deepgram. Archived in `versions/v1-sprint1-relay/`
- **v2-mvp** (2026-06-08): Direct-to-API architecture. Android → Deepgram directly. No backend.

---

*Document version: 2.0-MVP  
Last updated: 2026-06-08  
Author: kris_claw for Krishna Malik*
