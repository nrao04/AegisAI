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

- [ ] **2.1** Define a minimal **incident** model (e.g. in `backend/models/` or `backend/schemas/`): `id`, `title`, `severity`, `source`, `raw_log`, `created_at`, `status`.
- [ ] **2.2** Add a **Kafka consumer** in `backend/services/` that reads from the `logs` topic, parses each message, and creates an in-memory incident (or a simple list/dict for now). Log “Incident created: …” so you can verify.
- [ ] **2.3** Wire the consumer to run alongside the API (e.g. background task on startup) or as a separate script. Ensure one “test” log from the producer results in one incident logged.

---

## Phase 3: Persistence (PostgreSQL)

- [ ] **3.1** Add a **PostgreSQL** dependency and connection (e.g. `asyncpg` or keep `psycopg2`; use env vars for connection string). Create a `backend/db/` or `backend/database/` module.
- [ ] **3.2** Add an **incidents** table (columns matching your incident model). Provide a simple migration or init script (e.g. `CREATE TABLE` in a `scripts/` or `db/` folder).
- [ ] **3.3** When the consumer creates an incident, **insert it into PostgreSQL** instead of (or in addition to) in-memory. Verify with `psql` or a DB client.

---

## Phase 4: REST API for incidents

- [ ] **4.1** Add **GET /incidents** (list, with optional limit) and **GET /incidents/{id}** (single incident) using FastAPI. Read from PostgreSQL.
- [ ] **4.2** Add **PATCH /incidents/{id}** (e.g. update `status`: open → acknowledged → resolved). Validate with Pydantic.
- [ ] **4.3** Optionally add **POST /incidents** to create an incident manually (useful for testing). Document in OpenAPI (/docs).

---

## Phase 5: Search (Elasticsearch) — optional next

- [ ] **5.1** Run Elasticsearch locally (Docker). Add a small `backend/services/search.py` that indexes incident (or log) documents.
- [ ] **5.2** Add **GET /incidents/search?q=...** that queries Elasticsearch and returns matching incidents (or fallback to DB if you prefer to keep it simple first).

---

## Phase 6: Deployment & docs

- [ ] **6.1** Fill **deployment/docker-compose.yml**: backend, Kafka, PostgreSQL, (optional) Elasticsearch. One command to bring the stack up.
- [ ] **6.2** Write **docs/setup.md** (prerequisites, env vars, how to run backend + Kafka + DB + consumer).
- [ ] **6.3** Write **docs/architecture.md** (data flow, components, where incidents live and how they’re updated).

---

## Phase 7: Chatbot & frontend (later)

- [ ] **7.1** Implement **chatbot/bots.py**: connect to an LLM or rules engine; given “what’s broken?” call GET /incidents and summarize.
- [ ] **7.2** Bootstrap **frontend** (e.g. React/Next or Vue) with `package.json`, list incidents from GET /incidents, show detail on click.
- [ ] **7.3** Add a simple chat UI in the frontend that talks to the chatbot (or to an API that wraps the bot).

---

**Current recommended step:** Start with **1.1** (`.gitignore`), then **1.2** and **1.3** so your current code runs end-to-end with Kafka before adding the consumer.

---

## Docker vs Kubernetes (for this project)

- **Use Docker (and Docker Compose)** for AegisAI at this stage. It’s enough to run backend, Kafka, PostgreSQL, and Elasticsearch on one machine with a single `docker compose up`. No need for Kubernetes yet.
- **Kubernetes** is for when you need multi-server scaling, high availability, and complex orchestration. Revisit K8s later if you deploy to a cloud (e.g. GKE, EKS) and need that. For MVP and local/full-stack dev, Docker is the right choice.
