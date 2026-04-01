## AegisAI – Architecture

AegisAI is an **incident-centric observability system** built around a streaming pipeline:

logs → Kafka → consumers → PostgreSQL + Elasticsearch → FastAPI API → chatbot / frontend.

---

## High-level diagram

```text
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

## Components

### 1. Ingestion – Kafka and producers

- **Kafka** runs as the central log bus (`logs` topic).
- Producers (e.g. `backend/services/log_ingestion.py`) publish raw log lines to `logs`.
- Connection details are configured via `KAFKA_BOOTSTRAP` (default `127.0.0.1:9092`).

### 2. Processing – Kafka consumer

- The **log consumer** (`backend/services/log_consumer.py`) subscribes to `logs`.
- Each message is converted into an `Incident` (see `backend/schemas/incident.py`):
  - `id`, `title`, `severity`, `source`, `raw_log`, `created_at`, `status`.
- For every log message, the consumer:
  1. Ensures the PostgreSQL schema and Elasticsearch index exist (`init_db`, `init_index`).
  2. Inserts the incident into Postgres (`insert_incident`).
  3. Best-effort indexes the incident into Elasticsearch (`index_incident`).

This pipeline decouples **log production** from **incident processing**, and makes it easy to evolve the incident model over time.

### 3. Storage – PostgreSQL

- PostgreSQL is the **source of truth** for incidents.
- The `incidents` table is created automatically if missing:
  - `id TEXT PRIMARY KEY`
  - `title TEXT`
  - `severity TEXT`
  - `source TEXT`
  - `raw_log TEXT`
  - `created_at TIMESTAMPTZ`
  - `status TEXT`
- Access is encapsulated in `backend/db.py`:
  - `init_db`, `insert_incident`, `get_incident`, `get_incidents`.

### 4. Search – Elasticsearch

- Elasticsearch provides **full-text search** over incidents.
- `backend/services/search.py`:
  - `init_index` creates an `incidents` index with mappings for id, title, severity, source, raw_log, created_at, status.
  - `index_incident` writes documents as incidents are created.
  - `search_incidents` runs multi-field queries across title, raw_log, severity, and source.
- The backend exposes this via `GET /incidents/search`.

### 5. API – FastAPI

- `backend/main.py` defines the HTTP API:
  - `GET /` – welcome / health.
  - `GET /incidents?limit=` – list incidents from Postgres.
  - `GET /incidents/{id}` – fetch a single incident.
  - `PATCH /incidents/{id}` – update incident status (open → acknowledged → resolved).
  - `POST /incidents` – manually create incidents (useful for tests).
  - `GET /incidents/search?q=` – search incidents via Elasticsearch.
- The Kafka consumer runs as a separate process (or container), reading from the same Kafka topic and writing to Postgres and Elasticsearch; the API only reads from the stores.

### 6. Chatbot – AI and automation layer

- The chatbot layer (`backend/services/chatbot.py`) is the bridge between **natural language questions** and the incident API.
- Given a question like “What’s broken right now?”, the bot:
  - Calls the incidents API to fetch recent incidents.
  - Uses Claude (via the Anthropic API) to generate a rich, context-aware answer.
  - Falls back to rule-based aggregation by severity/status if no API key is configured.
- Exposed via `POST /chat` on the FastAPI backend.
- Future extensions:
  - Trigger or suggest runbook steps and automations.
  - Persistent chat history per incident.

### 7. Frontend – Operator dashboard

- The frontend (in `frontend/`) is a lightweight dashboard:
  - Fetches `GET /incidents` and lists current incidents.
  - Shows metadata and raw log details when an incident is selected.
  - Includes a simple “chat-style” input that can ask “what’s broken?” and display a summary based on the incidents API.
- It is intentionally minimal and framework-agnostic for now so it’s easy to run locally.

---

## Data flow summary

1. **Logs in** – Services emit log lines to Kafka’s `logs` topic.
2. **Consumer** – The log consumer translates each log into an `Incident` object.
3. **Persistence** – Incidents are written to PostgreSQL (durable, queryable history).
4. **Indexing** – Incidents are indexed into Elasticsearch for flexible search.
5. **Access** – FastAPI exposes REST endpoints for listing, searching, and updating incidents.
6. **Experience** – The chatbot and frontend sit on top, turning raw telemetry into incident-centric views and narratives focused on customer impact.

