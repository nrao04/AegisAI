# AegisAI — Step-by-step plan

Follow these in order. Complete one step (and test it) before moving to the next.

---

## Phase 1: Local dev & infra (run what you have)

- [x] **1.1** Add a proper `.gitignore` (e.g. `venv/`, `__pycache__/`, `.env`, `node_modules/`).
- [x] **1.2** Run the backend: `cd backend && pip install -r requirements.txt && python main.py` → confirm http://localhost:8000 and /docs work.
- [x] **1.3** Start Kafka locally. Pick one:
  - **Option A (recommended):** Install [Docker Desktop](https://www.docker.com/products/docker-desktop/), then from the **project root (AegisAI/)** run:
    `docker compose -f deployment/docker-compose.yml up -d`
  - **Option B (no Docker):** Install Kafka via Homebrew: `brew install kafka` then `brew services start zookeeper` and `brew services start kafka`. Broker will be on `localhost:9092`.
- [x] **1.4** Run the log producer: `python -m services.log_ingestion` from `backend/` (with `.venv` active). Confirm the message is produced (check Kafka topic or logs).

---

## Phase 2: Kafka consumer & incident model

- [x] **2.1** Define a minimal **incident** model (in `backend/schemas/incident.py`): `id`, `title`, `severity`, `source`, `raw_log`, `created_at`, `status`, `tenant`.
- [x] **2.2** Add a **Kafka consumer** in `backend/services/log_consumer.py` that reads from the `logs` topic, parses each message, and creates an incident. Includes deterministic IDs (partition+offset), deduplication (5-min window), and Slack notifications.
- [x] **2.3** Wire the consumer to run alongside the API or as a separate `log-consumer` Docker service.

---

## Phase 3: Persistence (PostgreSQL)

- [x] **3.1** Add PostgreSQL dependency and `ThreadedConnectionPool` (`backend/db.py`), configured via `DATABASE_URL`.
- [x] **3.2** `incidents` table + `incident_events` audit table auto-created by `init_db()` on startup.
- [x] **3.3** Consumer and API both write incidents to PostgreSQL. Events (created, status_change, runbook_generated) logged to `incident_events`.

---

## Phase 4: REST API for incidents

- [x] **4.1** `GET /incidents` and `GET /incidents/{id}` — read from PostgreSQL.
- [x] **4.2** `PATCH /incidents/{id}` — update status; logs `status_change` event; fires Slack alert on resolve.
- [x] **4.3** `POST /incidents` — manual creation. `POST /ingest` — HTTP log ingest without Kafka.
- [x] **4.4** `GET /stats` — 24-hour operational stats (open, resolved, high, medium counts).
- [x] **4.5** `GET /incidents/{id}/events` — full audit trail per incident.

---

## Phase 5: Search (Elasticsearch)

- [x] **5.1** `backend/services/search.py` with `init_index`, `index_incident`, `search_incidents`. Thread-safe singleton with graceful degradation.
- [x] **5.2** `GET /incidents/search?q=...` — full-text Elasticsearch search; returns empty list if ES unavailable.

---

## Phase 6: Deployment & docs

- [x] **6.1** `deployment/docker-compose.yml` — postgres, elasticsearch, kafka, backend, log-consumer, frontend (nginx). All services with `restart: unless-stopped` and health checks.
- [x] **6.2** `docs/setup.md` — prerequisites, env vars, how to run full stack.
- [x] **6.3** `docs/architecture.md` — data flow, components, incident lifecycle.
- [x] **6.4** `.env.example` — all required environment variables documented.

---

## Phase 7: Chatbot & frontend

- [x] **7.1** `backend/services/chatbot.py` — Claude-powered AI assistant with rule-based fallback. `POST /chat` endpoint.
- [x] **7.2** `frontend/index.html` — futuristic dark dashboard (glassmorphism, design tokens, severity color coding).
- [x] **7.3** `frontend/app.js` — WebSocket real-time feed, filters, full-text search, chat, runbook generation, audit timeline.

---

## Phase 8: AI runbooks, Slack alerts, real-time (completed)

- [x] **8.1** `backend/services/runbook.py` — `POST /incidents/{id}/runbook` generates a 4-section AI remediation playbook via Claude (template fallback when no API key).
- [x] **8.2** `backend/services/notifier.py` — Slack Block Kit alerts for HIGH/CRITICAL incidents on create and resolve.
- [x] **8.3** WebSocket broadcaster (`/ws/incidents`) — pushes incident list to all connected clients within 5 s of any change.
- [x] **8.4** Deduplication — `check_duplicate()` with 5-minute window suppresses alert storms from repeated log errors.
- [x] **8.5** Audit trail — every create, status change, and runbook generation logged to `incident_events`; visible in the frontend timeline.

---

## Phase 9: Potential next improvements

- [ ] **9.1** **Authentication** — JWT or API-key auth on all endpoints; per-tenant access control.
- [ ] **9.2** **Incident correlation** — group related incidents by pattern matching or embedding similarity.
- [ ] **9.3** **MTTR / MTTD metrics** — time-to-detect and time-to-resolve dashboards.
- [ ] **9.4** **Multi-source ingestion** — AWS CloudWatch, Datadog, PagerDuty, webhook adapters.
- [ ] **9.5** **Alerting rules** — configurable thresholds (e.g. "alert if >10 HIGH incidents in 1 min").
- [ ] **9.6** **Persistent chat history** — store and recall conversation context across sessions.
- [ ] **9.7** **Runbook versioning** — diff runbooks over time; allow operator edits.
