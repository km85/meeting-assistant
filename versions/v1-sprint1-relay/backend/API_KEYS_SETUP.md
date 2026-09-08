# Meeting Assistant - API Key Setup Guide

## ⚠️ SECURITY WARNING
**NEVER share API keys in chat, email, or public channels!**

## 🔑 Required API Keys

### 1. Deepgram API Key
1. Go to [deepgram.com](https://deepgram.com)
2. Sign up for free account (gets $200 credits)
3. Go to Console → API Keys
4. Create new key: `meeting-assistant`
5. Copy the key

### 2. OpenAI API Key
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign in with your ChatGPT Plus account
3. Go to API Keys → Create new secret key
4. Name: `meeting-assistant`
5. Copy the key (save it - shown only once!)

### 3. Telegram Bot Token
1. Open Telegram, search [@BotFather](https://t.me/BotFather)
2. Send `/newbot`
3. Name: `Meeting Assistant`
4. Username: `yourname_meeting_bot` (must end in _bot)
5. Copy the token

### 4. Telegram Chat ID
- Your chat ID is: `134036214`
- (This is your Telegram user ID)

### 5. Backend Auth Token (Generate Random)
```bash
openssl rand -hex 32
```

## 🛠️ Setup Steps

### Option A: Direct on Server (Recommended)
```bash
cd meeting-assistant/backend

# Create .env file
nano .env
```

Paste this (fill in your keys):
```env
DEEPGRAM_API_KEY=your_deepgram_key_here
OPENAI_API_KEY=your_openai_key_here
TELEGRAM_BOT_TOKEN=your_telegram_token_here
TELEGRAM_CHAT_ID=134036214
BACKEND_AUTH_TOKEN=your_random_generated_token
TRANSCRIPT_STORAGE_ENABLED=false
RAW_AUDIO_STORAGE_ENABLED=false
```

Save: `Ctrl+O`, `Enter`, `Ctrl+X`

```bash
# Run setup
chmod +x setup.sh
./setup.sh

# Start server
conda activate meeting-assistant
python -m app.main
```

### Option B: Using 1Password/Bitwarden
1. Save keys in password manager
2. Share secure link (if needed)
3. Copy-paste into `.env` on server

### Option C: GitHub Secrets (if deploying to cloud)
1. Go to repository Settings → Secrets
2. Add each key as repository secret
3. Use in GitHub Actions workflow

## ✅ Verify Setup

Test endpoints:
```bash
# Health check
curl http://localhost:8000/health

# Test Telegram
curl -X POST http://localhost:8000/telegram/test

# Check sessions
curl http://localhost:8000/session/status
```

## 🔒 Security Checklist
- [ ] `.env` file in `.gitignore`
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] No keys in code or logs
- [ ] Regular key rotation
- [ ] Separate keys for dev/prod

## 🆘 Troubleshooting

### Deepgram not working?
- Check key starts with `dg_`
- Verify account has credits
- Check region: `api.deepgram.com`

### OpenAI not working?
- Check key starts with `sk-`
- Verify billing is set up
- Check rate limits

### Telegram not working?
- Verify bot token format: `123456:ABC-DEF...`
- Check bot is started (send `/start` to bot)
- Verify chat ID is correct

## 📞 Need Help?
If stuck on any step, describe the error (without sharing keys!) and I'll help debug.
