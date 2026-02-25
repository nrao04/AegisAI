# AegisAI

**AI-powered incident response system** — ingest logs, detect anomalies, and respond with automation and AI-assisted workflows.

---

## Overview

AegisAI is a unified platform for operational incident management. It ingests application and infrastructure logs via a streaming pipeline (Kafka), persists incidents in PostgreSQL, indexes them in Elasticsearch for search, and exposes a REST API plus a minimal operator dashboard and chat-style “what’s broken?” summary.

---

## Features

| Area | Status | Description |
|------|--------|-------------|
| **REST API** | ✅ | FastAPI: list/search/get/patch/post incidents, health check |
| **Log ingestion** | ✅ | Kafka producer for streaming logs to a `logs` topic |
| **Search & storage** | ✅ | Elasticsearch full-text search + PostgreSQL source of truth |
| **Chatbot** | ✅ | Rule-based “what’s broken?” summary (extensible to LLM) |
| **Frontend** | ✅ | Operator dashboard: incident list, detail, and chat UI |
| **Deployment** | ✅ | Docker Compose: one command to run full stack |

---

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Logs /    │────▶│   Kafka     │────▶│  Consumers &    │
│   Sources   │     │   (logs)    │     │  Processing     │
└─────────────┘     └─────────────┘     └────────┬────────┘
                                                 │
         ┌───────────────────────────────────────┼───────────────────────────────────────┐
         │                                       │                                       │
         ▼                                       ▼                                       ▼
┌─────────────────┐                   ┌─────────────────┐                   ┌─────────────────┐
│  Elasticsearch  │                   │   PostgreSQL    │                   │   FastAPI       │
│  (search/agg)   │                   │  (incidents)    │                   │   (API)         │
└─────────────────┘                   └─────────────────┘                   └────────┬────────┘
                                                                                     │
         ┌───────────────────────────────────────┼───────────────────────────────────────┐
         │                                       │                                       │
         ▼                                       ▼                                       ▼
┌─────────────────┐                   ┌─────────────────┐                   ┌─────────────────┐
│   Frontend      │                   │   Chatbot       │                   │   External      │
│   (dashboard)   │                   │   (AI layer)    │                   │   integrations  │
└─────────────────┘                   └─────────────────┘                   └─────────────────┘
```

---

## Project structure

```
AegisAI/
├── backend/                    # FastAPI application
│   ├── main.py                 # API entrypoint, CORS, health
│   ├── db.py                   # PostgreSQL access (incidents)
│   ├── requirements.txt
│   ├── schemas/
│   │   └── incident.py         # Pydantic incident model
│   └── services/
│       ├── log_ingestion.py    # Kafka producer
│       ├── log_consumer.py     # Kafka → Postgres + Elasticsearch
│       └── search.py           # Elasticsearch indexing & search
├── chatbot/
│   └── bots.py                 # “What’s broken?” summary (API client)
├── frontend/
│   ├── index.html              # Dashboard + chat UI
│   ├── app.js                  # Incidents list, detail, chat
│   └── package.json
├── deployment/
│   └── docker-compose.yml     # Postgres, ES, Kafka, backend, log-consumer
├── docs/
│   ├── architecture.md
│   ├── setup.md
│   ├── NEXT_STEPS.md
└── README.md
```

---

## Prerequisites

- **Python** 3.10+
- **Kafka** (broker on `localhost:9092`) — required for log ingestion. Use either:
  - **Docker:** run Kafka via `deployment/docker-compose.kafka-only.yml`, or
  - **Homebrew (no Docker):** `brew install kafka` then start Zookeeper and Kafka.
- **Docker** (optional for now, recommended later) — for full-stack run (backend + Kafka + Postgres + Elasticsearch). See [Docker vs Kubernetes](#docker-vs-kubernetes) in `docs/NEXT_STEPS.md`.

---

## Quick start (full stack)

**Recommended for demo:** from project root run:

```bash
docker compose -f deployment/docker-compose.yml up --build
```

Wait ~30 seconds for Kafka and Elasticsearch to be ready. Then open **http://localhost:8000/docs** for the API and optionally serve the frontend (see [docs/setup.md](docs/setup.md)).

### Backend only (API)

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

API: **http://localhost:8000**  
Docs: **http://localhost:8000/docs**

### 2. Log ingestion (Kafka producer)

With a Kafka broker running on `localhost:9092`:

```bash
cd backend
source .venv/bin/activate
python -m services.log_ingestion
```

Sends a sample log message to the `logs` topic. Extend `log_ingestion.py` for real sources (files, HTTP, agents).

### Tests

From `backend/` with a venv and `DATABASE_URL` set (e.g. full stack running via Docker):

```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="postgresql://aegis:aegis@localhost:5432/aegisai" pytest tests/ -v
```

Or from the backend container: `docker compose -f deployment/docker-compose.yml exec backend pytest tests/ -v`

---

## Tech stack

| Layer | Technology |
|-------|------------|
| API | FastAPI, Uvicorn, Pydantic |
| Streaming | Kafka (aiokafka, kafka-python) |
| Search | Elasticsearch |
| Database | PostgreSQL (psycopg2) |
| Frontend | *(TBD)* |
| Deployment | *(Docker Compose planned)* |

---

## Roadmap

- [x] Kafka consumer to process `logs` and persist incidents (Postgres + Elasticsearch)
- [x] Incident CRUD and search APIs in FastAPI
- [x] Chatbot in `chatbot/bots.py` (“what’s broken?”, severity/status summary)
- [x] Frontend dashboard (incident list, detail, chat UI)
- [x] `deployment/docker-compose.yml` for full stack
- [x] `docs/architecture.md` and `docs/setup.md`
- [ ] Optional: LLM-backed chatbot, runbooks, more frontend polish

---

## Contributing

1. Fork the repo and create a branch from `main`.
2. Follow existing patterns (FastAPI in `backend/`, services under `backend/services/`).
3. Add or update tests and docs as needed.
4. Open a PR with a short description of changes and how to test them.

---

## License

MIT License
