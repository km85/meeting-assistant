# Meeting Assistant

AI-powered privacy-first meeting assistant. BYOK (Bring Your Own Key). Local-first. No backend.

## Versions

### Current: v2-mvp (In Development)
- **Architecture:** Direct-to-API (Android → Deepgram → OpenAI → Telegram)
- **No backend needed.** Everything runs on the user's phone.
- **Location:** `v2-mvp/`
- **Status:** Planning complete, development starts Week 1
- **Docs:** [Architecture v2](v2-mvp/docs/Architecture-v2.md)

### Archived: v1-sprint1
- **Architecture:** Backend relay (Android → VPS → Deepgram → OpenAI → Telegram)
- **Status:** Archived. Proof-of-concept that validated audio recording and API integration.
- **Location:** `versions/v1-sprint1-relay/`
- **Code:** Kotlin Android + FastAPI backend + Docker

## Documentation

| Document | Description |
|----------|-------------|
| [MVP-Architecture.md](docs/MVP-Architecture.md) | Initial v2 architecture draft (superseded by v2-mvp/docs/Architecture-v2.md) |
| [PARKING-LOT.md](docs/PARKING-LOT.md) | Future ideas, features, revenue channels — parked for later review |
| [reusability-analysis.md](docs/reusability-analysis.md) | What we can reuse from v1-sprint1 |
| [v2-mvp/docs/Architecture-v2.md](v2-mvp/docs/Architecture-v2.md) | Current v2 MVP architecture (direct-to-API) |

## Product

- **Platform:** Android (Kotlin native)
- **Price:** $50 lifetime (base app + 1 mode), $10 per additional mode DLC
- **Free trial:** 7 days
- **Distribution:** Direct website download (no Play Store)
- **Target:** Privacy-conscious corporate users who can't install software on company laptops

## Tech Stack (v2-mvp)

- **Android:** Kotlin + Room (SQLite) + OkHttp (WebSocket + HTTP)
- **STT:** Deepgram (direct WebSocket from phone)
- **LLM:** OpenAI GPT-4o-mini (fast) + GPT-5.5 (deep analysis)
- **Output:** Telegram Bot (user's own bot, polling from app)
- **Storage:** SQLite local-only
- **Payment:** Stripe + serverless license validation

## Status

🚧 **MVP Week 1:** Audio test app — recording + Deepgram direct connection

---

*Last updated: 2026-06-08*
