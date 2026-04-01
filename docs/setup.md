## AegisAI – Setup guide

This guide walks you through running the full AegisAI stack locally: **backend API**, **Kafka**, **PostgreSQL**, and **Elasticsearch**.

---

## 1. Prerequisites

- **Python** 3.10+
- **Docker** and **Docker Compose**
- Optional: `psql` (PostgreSQL CLI) and an HTTP client (`curl`, Postman, or browser).

---

## 2. Environment variables

The backend reads its configuration from environment variables (sensible defaults are provided in Docker):

- **`DATABASE_URL`** – PostgreSQL connection string  
  - Example (local/dev): `postgresql://aegis:aegis@localhost:5432/aegisai`
- **`ELASTICSEARCH_URL`** – Elasticsearch URL  
  - Default: `http://localhost:9200`
- **`ELASTICSEARCH_INDEX`** – Elasticsearch index name  
  - Default: `incidents`
- **`KAFKA_BOOTSTRAP`** – Kafka bootstrap servers  
  - Default: `127.0.0.1:9092`

When running via Docker Compose, these are already set for the backend container.

---

## 3. Run the full stack with Docker Compose

From the project root (`AegisAI/`):

```bash
docker compose -f deployment/docker-compose.yml up --build
```

This brings up:

- `postgres` on `localhost:5432`
- `elasticsearch` on `localhost:9200`
- `kafka` on `localhost:9092`
- `backend` on `http://localhost:8000`

Give Kafka and Elasticsearch **15–30 seconds** to finish booting before sending traffic.

To stop everything:

```bash
docker compose -f deployment/docker-compose.yml down
```

---

## 4. Running services manually (without Docker)

If you prefer to run pieces yourself:

1. **PostgreSQL**
   - Start a local Postgres instance (via Homebrew, Docker, etc.).
   - Create database and user:
     ```bash
     createdb aegisai
     createuser aegis --pwprompt   # choose a password
     ```
   - Export `DATABASE_URL`, e.g.:
     ```bash
     export DATABASE_URL="postgresql://aegis:<password>@localhost:5432/aegisai"
     ```

2. **Elasticsearch**
   - Easiest via Docker:
     ```bash
     docker run --name aegis-es -p 9200:9200 \
       -e "discovery.type=single-node" \
       -e "xpack.security.enabled=false" \
       -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
       docker.elastic.co/elasticsearch/elasticsearch:8.13.4
     ```

3. **Kafka**
   - Use the provided Kafka-only compose:
     ```bash
     docker compose -f deployment/docker-compose.kafka-only.yml up -d
     ```
   - This starts a single-broker KRaft Kafka (no Zookeeper) on `localhost:9092`.
   - Or use any other local Kafka that listens on `127.0.0.1:9092`.

4. **Backend API + consumer**
   - In a terminal:
     ```bash
     cd backend
     python -m venv .venv
     source .venv/bin/activate
     pip install -r requirements.txt
     python main.py
     ```
   - The FastAPI app will start on `http://localhost:8000` and the Kafka consumer will run in a background task, creating incidents and persisting them into Postgres (and indexing into Elasticsearch).

5. **Seed demo data**
   - With the backend running, populate the dashboard with realistic incidents:
     ```bash
     python backend/seed.py
     ```
   - This ingests 11 incidents across two tenants with mixed severities and statuses.
   - To send a single raw log via Kafka instead (useful for testing the consumer pipeline):
     ```bash
     cd backend
     source .venv/bin/activate
     python -m services.log_ingestion
     ```

---

## 5. Verifying the system

1. **Check the API**
   - Open `http://localhost:8000` in a browser – you should see the welcome JSON.
   - Open `http://localhost:8000/docs` – FastAPI’s interactive docs.

2. **List incidents**
   - Use the `/incidents` endpoint (GET) to fetch incidents from Postgres.
   - You should see the incident created from the sample log.

3. **Search incidents**
   - Use `/incidents/search?q=error` to query Elasticsearch.
   - If Elasticsearch is not available, this will return an empty list but the API will remain healthy.

4. **Update status**
   - Use `PATCH /incidents/{id}` with a JSON body like:
     ```json
     { "status": "acknowledged" }
     ```
   - Confirm the updated status via `GET /incidents/{id}`.


