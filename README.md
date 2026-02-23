# AegisAI

**AI-powered incident response system** — ingest logs, detect anomalies, and respond with automation and AI-assisted workflows.

---

## Overview

AegisAI is a unified platform for operational incident management. It ingests application and infrastructure logs via a streaming pipeline, stores and indexes them for search, and (as the project evolves) will support AI-driven analysis, chatbot-style queries, and automated or suggested remediation.

*Current phase: foundation — API, log ingestion pipeline, and stack choices are in place; chatbot, frontend, and full deployment are planned.*

---

## Features

| Area | Status | Description |
|------|--------|-------------|
| **REST API** | ✅ | FastAPI backend with health/welcome endpoint |
| **Log ingestion** | ✅ | Kafka producer for streaming logs to a `logs` topic |
| **Search & storage** | 📋 Planned | Elasticsearch + PostgreSQL (deps declared) |
| **Chatbot** | 📋 Planned | AI assistant for querying incidents and running actions |
| **Frontend** | 📋 Planned | Operator dashboard and incident UI |
| **Deployment** | 📋 Planned | Docker Compose for local/full-stack runs |

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
│   ├── main.py                 # App entrypoint, root/health endpoint
│   ├── requirements.txt        # Python dependencies
│   └── services/
│       └── log_ingestion.py    # Kafka producer for log streaming
├── chatbot/                    # AI / automation layer (planned)
│   └── bots.py
├── frontend/                   # Web UI (planned)
│   └── package.json
├── deployment/                 # Docker / orchestration (planned)
│   └── docker-compose.yml
├── docs/
│   ├── architecture.md
│   └── setup.md
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

## Quick start

### 1. Backend (API)

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

- [ ] Kafka consumer(s) to process `logs` and create/search incidents
- [ ] Elasticsearch indexing and Postgres schema for incidents
- [ ] Incident CRUD and search APIs in FastAPI
- [ ] Chatbot integration in `chatbot/bots.py` (e.g. “what’s down?”, runbooks)
- [ ] Frontend app (dashboard, incident list/detail)
- [ ] `deployment/docker-compose.yml` for backend + Kafka + Elasticsearch + Postgres (+ optional frontend)
- [ ] Fill `docs/architecture.md` and `docs/setup.md` with detailed design and runbooks

---

## Contributing

1. Fork the repo and create a branch from `main`.
2. Follow existing patterns (FastAPI in `backend/`, services under `backend/services/`).
3. Add or update tests and docs as needed.
4. Open a PR with a short description of changes and how to test them.

---

## License

MIT License
