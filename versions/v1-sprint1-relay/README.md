# Meeting Assistant

AI-powered real-time meeting assistant.

## Structure
- `backend/` - FastAPI + WebSocket + Deepgram + OpenAI
- `android/` - Android client app
- `.github/workflows/` - CI/CD

## Setup

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Environment Variables
```
DEEPGRAM_API_KEY=your_key
OPENAI_API_KEY=your_key
TELEGRAM_BOT_TOKEN=your_token
```

### Android
Requires Android Studio with SDK 34.

## Features
- Real-time speech-to-text via Deepgram
- AI answers via OpenAI GPT-4o
- Telegram bot integration
- WebSocket live streaming

## License
MIT
