# Meeting Assistant - Android MVP Setup Guide

## Android Core - Built ✅

### Files Created:
- `MainActivity.kt` — UI with Start/Stop/Test buttons
- `MeetingService.kt` — Foreground service + audio recording + WebSocket
- `WebSocketClient.kt` — WSS connection + Android Keystore auth token storage
- `MeetingAssistantApp.kt` — Application class
- `AndroidManifest.xml` — Permissions + service declaration
- `activity_main.xml` — Simple UI layout
- `build.gradle` (app + project) — Dependencies

### Security Features:
- Auth token encrypted in Android Keystore (AES/GCM)
- WSS (WebSocket Secure) for audio streaming
- TLS encrypted transport
- No local audio storage

---

## Backend .env Setup via SSH

### SSH Credentials
```
Host: srv1698532 (or your VPS IP)
User: root
Path: /root/.openclaw/workspace/meeting-assistant/backend
```

### Step 1: SSH ke Server
```bash
ssh root@srv1698532
# atau: ssh root@YOUR_VPS_IP
cd /root/.openclaw/workspace/meeting-assistant/backend
```

### Step 2: Generate Auth Token
```bash
openssl rand -hex 32
```
Copy the output — this is your `BACKEND_AUTH_TOKEN`.

### Step 3: Create .env File
```bash
cp .env.example .env
nano .env
```

### Step 4: Fill in Your Keys
```env
DEEPGRAM_API_KEY=your_d…here
OPENAI_API_KEY=your_o…here
TELEGRAM_BOT_TOKEN=your_t…here
TELEGRAM_CHAT_ID=134036214
BACKEND_AUTH_TOKEN=your_g…ep_2
TRANSCRIPT_STORAGE_ENABLED=false
RAW_AUDIO_STORAGE_ENABLED=false
```

**Get your keys from:**
1. **Deepgram:** https://deepgram.com → Sign up → API Keys → Create key
2. **OpenAI:** https://platform.openai.com → API Keys → Create new secret key
3. **Telegram Bot:** Message @BotFather → /newbot → copy token

### Step 5: Secure the File
```bash
chmod 600 .env
```

### Step 6: Install & Run Backend
```bash
# Check if conda environment exists
conda env list | grep meeting-assistant

# Kalau belum ada, create:
conda create -n meeting-assistant python=3.11 -y

# Activate
conda activate meeting-assistant

# Install dependencies
pip install -r requirements.txt

# Run server
python -m app.main
```

Server akan jalan di `http://0.0.0.0:8000`

### Step 7: Test Backend (buka terminal baru)
```bash
ssh root@srv1698532

# Test health check
curl http://localhost:8000/health

# Test Telegram bot
curl -X POST http://localhost:8000/telegram/test

# Check active sessions
curl http://localhost:8000/session/status
```

Kalau semua OK, backend siap!

---

## Android App - Next Steps

### 1. Update Backend URL
In `WebSocketClient.kt`, replace:
```kotlin
private const val BACKEND_URL = "wss://your-backend.com/audio-stream"
```
with your actual backend URL.

**Kalau backend di VPS yang sama (no HTTPS/WSS yet):**
```kotlin
private const val BACKEND_URL = "ws://srv1698532:8000/audio-stream"
```

**Kalau sudah pakai HTTPS/WSS (recommended):**
```kotlin
private const val BACKEND_URL = "wss://your-domain.com/audio-stream"
```

### 2. Store Auth Token in Android
Add a one-time setup screen or hardcode for MVP:
```kotlin
// In MainActivity or setup screen
val wsClient = WebSocketClient()
wsClient.storeAuthToken("your_backend_auth_token_here")
```

### 3. Build APK
```bash
cd /root/.openclaw/workspace/meeting-assistant/android
./gradlew assembleDebug
```

APK will be at: `app/build/outputs/apk/debug/app-debug.apk`

---

## End-to-End Test Flow

1. **Start backend** on server
2. **Install APK** on Android phone
3. **Open app** → Tap "Test Connection" → Should show "OK"
4. **Tap "Start Listening"** → Notification shows "Listening..."
5. **Talk near phone** → Audio streams to backend
6. **Open Telegram** → Message your bot → `/assist` or `/recap`
7. **Bot replies** with real-time assistance based on transcript

---

## Security Checklist

- [ ] `.env` file has `chmod 600`
- [ ] `.env` in `.gitignore`
- [ ] No API keys in code or logs
- [ ] Android auth token stored in Keystore
- [ ] WSS (not WS) for WebSocket (production)
- [ ] Backend behind HTTPS/WSS (production)
- [ ] Telegram bot only sends to your chat ID

---

## Troubleshooting

### Android app won't install?
- Enable "Install from unknown sources" in Settings
- Check minSdk (26) vs your Android version

### WebSocket won't connect?
- Verify backend URL uses `wss://` (not `ws://`) for production
- Check firewall: port 443/8000 open
- Verify auth token matches `.env`

### Deepgram not transcribing?
- Check API key starts with `dg_`
- Verify audio format: 16kHz, 16-bit, mono PCM
- Check Deepgram console for usage/credits

### Telegram bot not responding?
- Send `/start` to bot first
- Verify bot token format: `123456:ABC-DEF...`
- Check `TELEGRAM_CHAT_ID` matches your user ID

---

Need help? Describe the error (without sharing keys!) and I'll debug.
