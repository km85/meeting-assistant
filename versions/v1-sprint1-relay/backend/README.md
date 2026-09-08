# Meeting Assistant Backend

## Setup

1. Create `.env` file from example:
```bash
cp .env.example .env
# Edit .env with your API keys
```

2. Install dependencies:
```bash
conda activate meeting-assistant
pip install -r requirements.txt
```

3. Run server:
```bash
python -m app.main
```

## API Endpoints

- `GET /health` — Health check
- `POST /telegram/test` — Send test message
- `GET /session/status` — Active sessions
- `WS /audio-stream` — Audio streaming WebSocket
- `GET /metrics/latency` — Latency metrics

## Project Endpoints

- `POST /projects/create` — Create project
- `GET /projects/list` — List projects
- `POST /projects/{id}/upload` — Upload document
- `GET /projects/{id}/status` — Project status
- `DELETE /projects/{id}` — Delete project

## Telegram Commands

- `/start` — Show help
- `/assist` — Real-time help
- `/say` — Answer latest question
- `/followup` — Suggest follow-up questions
- `/recap` — Meeting summary
- `/stop` — End session
- `/status` — Check session status
- `/projects` — List projects
- `/use_project <name>` — Set active project
- `/project_status` — Check project status

## Security

- No raw audio storage by default
- No permanent transcript storage by default
- Audit logs for session start/stop and commands
- Android auth token validation
- Sensitive content not logged
