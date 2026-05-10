# Hawk Eye Backend (FastAPI)

Minimal FastAPI skeleton for camera registration, events, and alerts.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Configuration

Copy the example env file and adjust values:

```bash
cp .env.example .env
```

Key settings:
- DATABASE_URL (Postgres connection string)
- JWT_SECRET (change this)
- AUTH_REQUIRED (set true to require JWT auth)

## Run

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Endpoints
- GET /health
- POST /auth/register
- POST /auth/login
- POST /camera/register
- GET /camera/list
- POST /events
- GET /events
- POST /alerts
- GET /alerts
- GET /recordings
- WS /ws/alerts
