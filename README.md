# AegisAI

**AI-powered incident response system** — ingest logs, detect anomalies, and respond with AI-assisted runbooks, real-time dashboards, and Slack alerts.

---

## Features

| Area | Status | Description |
|------|--------|-------------|
| **Log ingestion** | ✅ | Kafka consumer + HTTP `/ingest` endpoint |
| **REST API** | ✅ | FastAPI: CRUD, search, ingest, stats, WebSocket |
| **Search & storage** | ✅ | Elasticsearch full-text + PostgreSQL source of truth |
| **Real-time dashboard** | ✅ | WebSocket feed with live incident list and stats |
| **AI chatbot** | ✅ | Claude-powered "what's broken?" with rule-based fallback |
| **AI runbooks** | ✅ | Per-incident remediation playbooks via Claude |
| **Audit trail** | ✅ | Full event timeline per incident (created, ack, resolved, runbook) |
| **Slack alerts** | ✅ | Webhook notifications for HIGH/CRITICAL incidents |
| **Deduplication** | ✅ | 5-minute window dedup to suppress alert storms |
| **Deployment** | ✅ | Docker Compose: one command for full stack |

---

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Log Sources    │────▶│    Kafka     │────▶│   Log Consumer      │
│  (HTTP /ingest) │     │  (logs topic)│     │  dedup · notify     │
└─────────────────┘     └──────────────┘     └──────────┬──────────┘
                                                         │
              ┌──────────────────────────────────────────┤
              │                                          │
              ▼                                          ▼
┌─────────────────────┐                    ┌─────────────────────┐
│   Elasticsearch     │                    │    PostgreSQL        │
│   (full-text search)│                    │  (incidents + events)│
└─────────────────────┘                    └──────────┬──────────┘
                                                       │
                                           ┌──────────▼──────────┐
                                           │      FastAPI        │
                                           │  REST · WS · /chat  │
                                           └──────────┬──────────┘
                              ┌────────────────────────┤
                              │                        │
                              ▼                        ▼
                  ┌─────────────────────┐  ┌─────────────────────┐
                  │   Frontend          │  │   Slack / webhooks  │
                  │  (dashboard + chat) │  │   (HIGH/CRITICAL)   │
                  └─────────────────────┘  └─────────────────────┘
```

---

## Project structure

```
AegisAI/
├── backend/
│   ├── main.py                 # API: incidents, ingest, chat, runbook, WebSocket
│   ├── db.py                   # PostgreSQL pool, incidents + events CRUD, stats
│   ├── schemas/
│   │   └── incident.py         # Pydantic incident model
│   ├── services/
│   │   ├── log_consumer.py     # Kafka → Postgres + Elasticsearch + dedup + notify
│   │   ├── log_ingestion.py    # Kafka producer (sample log sender)
│   │   ├── search.py           # Elasticsearch indexing & search
│   │   ├── chatbot.py          # AI chatbot (Claude + rule-based fallback)
│   │   ├── runbook.py          # AI runbook generation (Claude + template fallback)
│   │   └── notifier.py         # Slack Block Kit alerts
│   ├── tests/
│   │   └── test_api.py         # Integration tests (22 cases)
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html              # Futuristic dark dashboard UI
│   └── app.js                  # WebSocket, filters, search, runbook, timeline, chat
├── deployment/
│   └── docker-compose.yml      # postgres, elasticsearch, kafka, backend, frontend
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   └── NEXT_STEPS.md
├── .env.example                # All required environment variables
└── README.md
```

---

## Quick start

**Copy env config and bring the full stack up:**

```bash
cp .env.example .env
# Optional: add ANTHROPIC_API_KEY and SLACK_WEBHOOK_URL to .env

docker compose -f deployment/docker-compose.yml up --build
```

| Service | URL |
|---------|-----|
| Frontend dashboard | http://localhost:3000 |
| Backend API + docs | http://localhost:8000/docs |
| PostgreSQL | localhost:5432 |
| Elasticsearch | http://localhost:9200 |
| Kafka | localhost:9092 |

---

## Environment variables

See `.env.example` for all options. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL DSN |
| `ELASTICSEARCH_URL` | Yes | Elasticsearch base URL |
| `KAFKA_BOOTSTRAP` | Yes | Kafka broker address |
| `ANTHROPIC_API_KEY` | No | Enables Claude AI chatbot & runbooks |
| `SLACK_WEBHOOK_URL` | No | Enables HIGH/CRITICAL incident Slack alerts |

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/incidents` | List incidents (latest first, `?limit=`) |
| GET | `/incidents/{id}` | Single incident |
| POST | `/incidents` | Create incident manually |
| PATCH | `/incidents/{id}` | Update status (open → acknowledged → resolved) |
| GET | `/incidents/search` | Full-text search via Elasticsearch (`?q=`) |
| POST | `/ingest` | HTTP log ingest (no Kafka required) |
| POST | `/incidents/{id}/runbook` | Generate AI remediation runbook |
| GET | `/incidents/{id}/runbook` | Retrieve latest runbook |
| GET | `/incidents/{id}/events` | Audit trail for an incident |
| GET | `/stats` | 24h operational stats |
| POST | `/chat` | AI assistant (ask about current incidents) |
| WS | `/ws/incidents` | Real-time incident feed |
| GET | `/health` | Health check |

---

## Running tests

With the full stack running via Docker Compose:

```bash
docker compose -f deployment/docker-compose.yml exec backend pytest tests/ -v
```

Or locally (with `DATABASE_URL` set and PostgreSQL running):

```bash
cd backend
source .venv/bin/activate
DATABASE_URL="postgresql://aegis:aegis@localhost:5432/aegisai" pytest tests/ -v
```

---

## Tech stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn, Pydantic |
| Streaming | Kafka (aiokafka) |
| Search | Elasticsearch 8.x |
| Database | PostgreSQL 16 (psycopg2) |
| AI | Claude claude-opus-4-6 (Anthropic) |
| Frontend | Vanilla JS, WebSocket, CSS glassmorphism |
| Alerts | Slack Incoming Webhooks |
| Deployment | Docker Compose |

---

## Contributing

1. Fork the repo and create a branch from `main`.
2. Follow existing patterns (FastAPI in `backend/`, services under `backend/services/`).
3. Add or update tests for new endpoints.
4. Open a PR with a short description of changes and how to test them.

---

## License

MIT License
