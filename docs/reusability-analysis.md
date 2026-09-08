# Reusability Analysis: v1-sprint1 → v2-mvp

## v1-sprint1 Architecture

**Pattern:** Backend relay architecture
- Android app (thin client) → WebSocket → Backend (VPS) → Deepgram → OpenAI → Telegram
- Backend runs on user's VPS (178.62.216.144)
- Backend handles: Deepgram streaming, OpenAI calls, Telegram bot, session management, knowledge base
- Android only captures audio and sends to backend

## v2-mvp Architecture

**Pattern:** Direct-to-API architecture (no backend)
- Android app (fat client) → Deepgram (direct WSS) → OpenAI (direct HTTPS) → Telegram (direct HTTPS)
- Everything runs on the phone
- No backend needed for core functionality
- User provides API keys directly in app

---

## What's Reusable ✅

### 1. Android Audio Recording (HIGH VALUE)

**Source:** `v1-sprint1/android/app/src/main/java/com/krishna/meetingassistant/MeetingService.kt`

**Reusable parts:**
- `AudioRecord` setup (16kHz, mono, PCM 16-bit) — lines 78-95
- Foreground service with notification — lines 53-68, 127-149
- Background recording loop — lines 97-117
- Permissions handling (RECORD_AUDIO, FOREGROUND_SERVICE) — in `MainActivity.kt`

**Changes needed:**
- Instead of sending to `WebSocketClient` (backend), send to Deepgram WebSocket
- Remove `WebSocketClient.setServerIp()` calls

### 2. WebSocket Patterns (HIGH VALUE)

**Source:** `v1-sprint1/android/app/src/main/java/com/krishna/meetingassistant/WebSocketClient.kt`

**Reusable parts:**
- OkHttp WebSocket connection logic — `connect()` method
- Auto-reconnect on failure — `onFailure()` handler with 5s delay
- Binary message sending (`sendAudio()`)
- Connection state tracking (`isConnected`)

**Changes needed:**
- Change URL from `ws://$serverIp:8000/audio-stream` to `wss://api.deepgram.com/v1/listen`
- Add Deepgram auth header: `Authorization: Token $deepgramApiKey`
- Change message format (Deepgram expects different metadata than our backend)
- Remove `getAuthToken()` / `storeAuthToken()` (Android Keystore auth is overkill for MVP, use encrypted prefs)

### 3. UI Structure (MEDIUM VALUE)

**Source:** `v1-sprint1/android/app/src/main/java/com/krishna/meetingassistant/MainActivity.kt`

**Reusable parts:**
- Activity lifecycle — `onCreate()`, `onDestroy()`
- Permission request pattern — `hasAudioPermission()`, `requestAudioPermission()`
- Button click handlers — start/stop/test
- Status text updates
- SharedPreferences usage

**Changes needed:**
- Replace IP input with API key setup screen
- Add project/knowledge base management UI
- Add more screens (Setup, Settings, Projects)
- Replace "test connection to backend" with "test Deepgram connection" and "test OpenAI connection"

### 4. Prompt Engineering (HIGH VALUE)

**Source:** `v1-sprint1/backend/app/answer_generator.py`

**Reusable parts:**
- `SYSTEM_PROMPT` — meeting assistant persona
- `generate_recap()` — recap prompt template
- `generate_say()` — say prompt template with knowledge base injection
- `generate_followup()` — followup prompt template
- `generate_assist()` — assist prompt template with knowledge base
- Tradeoff framing style (acknowledge → explain → suggest)

**Changes needed:**
- Convert from Python async to Kotlin coroutines
- Adapt to mobile (smaller context windows, shorter prompts)
- Keep dual-model approach: fast (gpt-4o-mini) for assist/say, deep (gpt-5.5) for recap/followup

### 5. Telegram Command Structure (MEDIUM VALUE)

**Source:** `v1-sprint1/backend/app/telegram_commands.py`

**Reusable parts:**
- Command handlers: `/assist`, `/say`, `/followup`, `/recap`, `/stop`, `/status`
- Command response formatting (Markdown, emoji)
- Session validation ("No active session" checks)
- Latency tracking
- Project switching (`/use_project`, `/projects`)

**Changes needed:**
- Convert from Python `telegram.ext` to Kotlin HTTP polling
- Bot runs in Android app instead of backend
- Need to store `telegram_chat_id` in app
- Simpler error handling (no `log_audit` backend)

### 6. Session Manager Logic (MEDIUM VALUE)

**Source:** `v1-sprint1/backend/app/session_manager.py`

**Reusable parts:**
- Session data model (session_id, transcript, metadata, active_project_id)
- `get_latest_question()` — extract last question from transcript
- `get_recent_transcript(minutes=N)` — filter transcript by time
- `save_transcript()` — export to file

**Changes needed:**
- Convert from Python to Kotlin/SQLite
- Replace in-memory storage with SQLite
- Simplify (no need for multi-session backend, single session per phone)

### 7. Knowledge Base Concepts (LOW VALUE)

**Source:** `v1-sprint1/backend/app/knowledge_base.py`, `project_routes.py`

**Reusable parts:**
- Project model (id, name, description, context)
- Simple document storage (text files, not vector DB for MVP)
- Context injection into prompts

**Changes needed:**
- MVP doesn't need vector search (RAG) — just simple text context
- Store as SQLite TEXT field, not vector DB
- Simplify significantly (no CUDA, no embeddings)

---

## What's NOT Reusable ❌

### 1. Backend (FastAPI Server)

**Why not:** v2-mvp eliminates backend entirely.

**What to do:** Archive in `v1-sprint1-relay/`. Reference for prompt engineering and command logic only.

### 2. Docker / Docker Compose

**Why not:** No containers needed for a mobile-only app.

### 3. Deepgram STT Backend Wrapper

**Source:** `v1-sprint1/backend/app/stt_client.py`

**Why not:** The backend wrapped Deepgram. In v2, Android connects directly to Deepgram.

**What to keep:** Reference for Deepgram options (`model=nova-2`, `language=id`, `encoding=linear16`, etc.)

### 4. WebSocket to Backend Protocol

**Why not:** Custom protocol between Android and backend is replaced by direct Deepgram protocol.

**What to keep:** Reference for metadata format (session_id, device, timestamp).

### 5. Android Keystore Auth Token

**Why not:** Overkill for MVP. Use encrypted SharedPreferences instead.

---

## Build Strategy

**Recommended approach:**

1. **Start with audio test app** — Reuse `MeetingService.kt` audio recording, but stream directly to Deepgram
2. **Build on top of existing Kotlin project** — Don't create new Flutter project (existing Kotlin proves it works)
3. **Iterative replacement:**
   - Week 1: Replace backend WebSocket with Deepgram WebSocket
   - Week 2: Add OpenAI client in Android
   - Week 3: Add Telegram bot polling in Android
   - Week 4: Add SQLite storage + UI polish

---

## Verdict

**~60% of existing Android code is reusable.** The Kotlin foundation is solid. The backend is useful as reference but not needed.

**Key insight:** v1-sprint1 was actually a proof-of-concept that proved:
- ✅ Kotlin audio recording works
- ✅ WebSocket streaming works
- ✅ Foreground service works
- ✅ Deepgram integration works (via backend)
- ✅ Telegram bot works
- ✅ Prompt engineering works

v2-mvp just needs to **reconnect the pieces** — direct from Android to APIs instead of through backend.

**This is good news:** We're not starting from scratch. We have a proven foundation.
