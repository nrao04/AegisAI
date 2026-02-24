# AegisAI — Step-by-step plan

Follow these in order. Complete one step (and test it) before moving to the next.

---

## Phase 1: Local dev & infra (run what you have)

- [ ] **1.1** Add a proper `.gitignore` (e.g. `venv/`, `__pycache__/`, `.env`, `node_modules/`).
- [ ] **1.2** Run the backend: `cd backend && pip install -r requirements.txt && python main.py` → confirm http://localhost:8000 and /docs work.
- [ ] **1.3** Start Kafka locally. Pick one:
  - **Option A (recommended):** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then from the **project root (AegisAI/)** run:  
    `docker compose -f deployment/docker-compose.kafka-only.yml up -d`  
    (Or: `docker run -d -p 9092:9092 apache/kafka` for a single container.)
  - **Option B (no Docker):** Install Kafka via Homebrew: `brew install kafka` then `brew services start zookeeper` and `brew services start kafka`. Broker will be on `localhost:9092`.
- [ ] **1.4** Run the log producer: `python -m services.log_ingestion` from `backend/` (with `.venv` active). Confirm the message is produced (check Kafka topic or logs).

---

## Phase 2: Kafka consumer & incident model

- [x] **2.1** Define a minimal **incident** model (e.g. in `backend/models/` or `backend/schemas/`): `id`, `title`, `severity`, `source`, `raw_log`, `created_at`, `status`.
- [x] **2.2** Add a **Kafka consumer** in `backend/services/` that reads from the `logs` topic, parses each message, and creates an in-memory incident (or a simple list/dict for now). Log “Incident created: …” so you can verify.
- [x] **2.3** Wire the consumer to run alongside the API (e.g. background task on startup) or as a separate script. Ensure one “test” log from the producer results in one incident logged.

---

## Phase 3: Persistence (PostgreSQL)

- [x] **3.1** Add a **PostgreSQL** dependency and connection (e.g. `asyncpg` or keep `psycopg2`; use env vars for connection string). Create a `backend/db/` or `backend/database/` module.  
      → Implemented in `backend/requirements.txt` (via `psycopg2-binary`) and `backend/db.py`, using `DATABASE_URL` for configuration.
- [x] **3.2** Add an **incidents** table (columns matching your incident model). Provide a simple migration or init script (e.g. `CREATE TABLE` in a `scripts/` or `db/` folder).  
      → `db.init_db()` creates an `incidents` table with `id`, `title`, `severity`, `source`, `raw_log`, `created_at`, and `status` columns if it does not exist.
- [x] **3.3** When the consumer creates an incident, **insert it into PostgreSQL** instead of (or in addition to) in-memory. Verify with `psql` or a DB client.  
      → `services/log_consumer.py` now calls `insert_incident(incident)` from `db.py` and logs “Incident created and stored …”.

---

## Phase 4: REST API for incidents

- [x] **4.1** Add **GET /incidents** (list, with optional limit) and **GET /incidents/{id}** (single incident) using FastAPI. Read from PostgreSQL.  
      → Implemented in `backend/main.py` using `db.get_incidents` and `db.get_incident`.
- [x] **4.2** Add **PATCH /incidents/{id}** (e.g. update `status`: open → acknowledged → resolved). Validate with Pydantic.  
      → Implemented as `PATCH /incidents/{incident_id}` with `IncidentStatusUpdate` payload; persists via `insert_incident`.
- [x] **4.3** Optionally add **POST /incidents** to create an incident manually (useful for testing). Document in OpenAPI (/docs).  
      → Implemented as `POST /incidents` accepting an `Incident` body and storing it via `insert_incident`.

---

## Phase 5: Search (Elasticsearch) — optional next

- [x] **5.1** Run Elasticsearch locally (Docker). Add a small `backend/services/search.py` that indexes incident (or log) documents.  
      → Implemented in `backend/services/search.py` with `init_index`, `index_incident`, and `search_incidents`.
- [x] **5.2** Add **GET /incidents/search?q=...** that queries Elasticsearch and returns matching incidents (or fallback to DB if you prefer to keep it simple first).  
      → Implemented as `GET /incidents/search?q=...&limit=...` in `backend/main.py`, using `search_incidents`; returns an empty list if Elasticsearch is unavailable.

---

## Phase 6: Deployment & docs

- [x] **6.1** Fill **deployment/docker-compose.yml**: backend, Kafka, PostgreSQL, (optional) Elasticsearch. One command to bring the stack up.  
      → Implemented in `deployment/docker-compose.yml` with services for `backend`, `postgres`, `elasticsearch`, and `kafka`.
- [x] **6.2** Write **docs/setup.md** (prerequisites, env vars, how to run backend + Kafka + DB + consumer).  
      → Implemented as a full setup guide covering Docker Compose and manual runs.
- [x] **6.3** Write **docs/architecture.md** (data flow, components, where incidents live and how they’re updated).  
      → Implemented with an end-to-end architecture overview and component breakdown.

---

## Phase 7: Chatbot & frontend (later)

- [x] **7.1** Implement **chatbot/bots.py**: connect to an LLM or rules engine; given “what’s broken?” call GET /incidents and summarize.  
      → Implemented a lightweight rule-based bot in `chatbot/bots.py` that calls the incidents API and summarizes by severity/status.
- [x] **7.2** Bootstrap **frontend** (e.g. React/Next or Vue) with `package.json`, list incidents from GET /incidents, show detail on click.  
      → Implemented a minimal vanilla JS dashboard in `frontend/index.html` + `frontend/app.js` with `frontend/package.json` (simple `start` script).
- [x] **7.3** Add a simple chat UI in the frontend that talks to the chatbot (or to an API that wraps the bot).  
      → Implemented a basic chat box in the frontend that mimics the chatbot’s “what’s broken right now?” behavior client-side using the `/incidents` API.
