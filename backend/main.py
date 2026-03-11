import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from db import (
    check_duplicate,
    get_events,
    get_incident,
    get_incidents,
    get_stats,
    init_db,
    insert_incident,
    log_event,
)
from schemas import Incident
from services.search import search_incidents

# ── WebSocket state ───────────────────────────────────────────────────────────

_ws_clients: list[WebSocket] = []
_last_incident_count: int = -1


async def _incident_broadcaster():
    """Poll DB every 5 s; push full incident list to WS clients when count changes."""
    global _last_incident_count
    while True:
        await asyncio.sleep(5)
        if not _ws_clients:
            continue
        try:
            incidents = get_incidents(limit=100)
            if len(incidents) != _last_incident_count:
                _last_incident_count = len(incidents)
                payload = {
                    "type": "incidents",
                    "data": [i.model_dump(mode="json") for i in incidents],
                }
                dead = []
                for ws in list(_ws_clients):
                    try:
                        await ws.send_json(payload)
                    except Exception:
                        dead.append(ws)
                for ws in dead:
                    if ws in _ws_clients:
                        _ws_clients.remove(ws)
        except Exception:
            pass


# ── App & lifespan ────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    task = asyncio.create_task(_incident_broadcaster())
    yield
    task.cancel()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Basic ─────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "Welcome to AegisAI – AI-Powered Incident Response System"}


@app.get("/health")
def health():
    try:
        get_incidents(limit=1)
        db_ok = True
    except Exception:
        db_ok = False
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "error"}


@app.get("/stats")
def stats():
    """Live operational stats for the last 24 hours."""
    return get_stats()


# ── Incidents ─────────────────────────────────────────────────────────────────

@app.get("/incidents", response_model=List[Incident])
def list_incidents(limit: int = Query(default=100, ge=1, le=1000)):
    return get_incidents(limit=limit)


@app.get("/incidents/search", response_model=List[Incident])
def search_incidents_endpoint(q: str, limit: int = Query(default=50, ge=1, le=1000)):
    return search_incidents(query=q, limit=limit)


@app.get("/incidents/{incident_id}", response_model=Incident)
def read_incident(incident_id: str):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="New status: open | acknowledged | resolved")


@app.patch("/incidents/{incident_id}", response_model=Incident)
def update_incident_status(incident_id: str, payload: IncidentStatusUpdate):
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    old_status = incident.status
    incident.status = payload.status
    insert_incident(incident)
    log_event(incident_id, "status_change", f"{old_status} → {payload.status}")

    if payload.status == "resolved":
        from services.notifier import notify_resolved
        notify_resolved(incident)

    return incident


@app.post("/incidents", response_model=Incident)
def create_incident(incident: Incident):
    insert_incident(incident)
    log_event(incident.id, "created", incident.title)
    return incident


# ── HTTP ingest (no Kafka required) ──────────────────────────────────────────

class IngestRequest(BaseModel):
    log: str = Field(..., min_length=1)
    source: str = "http"
    tenant: str = "default"


@app.post("/ingest", response_model=Incident)
def ingest_log(body: IngestRequest):
    """
    Ingest a raw log line directly over HTTP — no Kafka needed.

    Duplicates (same log from same source within 5 min) are silently dropped.
    """
    import re
    from uuid import uuid4

    raw = body.log.strip()
    title = raw[:80] + ("..." if len(raw) > 80 else "")
    severity = "high" if "error" in raw.lower() else "medium"

    # Override tenant if encoded in the log itself
    m = re.search(r"tenant[=:](\w+)", raw, re.IGNORECASE)
    tenant = m.group(1).lower() if m else body.tenant

    incident = Incident(
        id=str(uuid4()),
        title=title,
        severity=severity,
        source=body.source,
        tenant=tenant,
        raw_log=raw,
        created_at=datetime.utcnow(),
        status="open",
    )

    if check_duplicate(incident.title, incident.source):
        # Return existing deduplicated incident without creating a new row
        return incident

    insert_incident(incident)
    log_event(incident.id, "created", incident.title)

    from services.notifier import notify_new_incident
    notify_new_incident(incident)

    from services.search import index_incident
    index_incident(incident)

    return incident


# ── Runbook ───────────────────────────────────────────────────────────────────

class RunbookResponse(BaseModel):
    runbook: str


@app.post("/incidents/{incident_id}/runbook", response_model=RunbookResponse)
def generate_runbook(incident_id: str):
    """
    Generate an AI-powered remediation runbook for an incident.

    Result is stored in the incident's event log for future retrieval.
    Uses Claude if ANTHROPIC_API_KEY is set; falls back to a structured template.
    """
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    from services.runbook import generate
    text = generate(incident)
    log_event(incident_id, "runbook_generated", text)
    return {"runbook": text}


@app.get("/incidents/{incident_id}/runbook", response_model=RunbookResponse)
def get_latest_runbook(incident_id: str):
    """Return the most recently generated runbook for an incident."""
    events = get_events(incident_id)
    for ev in reversed(events):
        if ev["event_type"] == "runbook_generated":
            return {"runbook": ev["note"]}
    raise HTTPException(status_code=404, detail="No runbook generated yet")


# ── Event timeline ────────────────────────────────────────────────────────────

@app.get("/incidents/{incident_id}/events")
def incident_events(incident_id: str):
    """Return the full audit trail for an incident."""
    if not get_incident(incident_id):
        raise HTTPException(status_code=404, detail="Incident not found")
    events = get_events(incident_id)
    # Redact runbook text from timeline listing (it's big; use /runbook endpoint)
    return [
        {
            "event_type": e["event_type"],
            "note": e["note"] if e["event_type"] != "runbook_generated" else "Runbook generated",
            "created_at": e["created_at"],
        }
        for e in events
    ]


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)


class ChatResponse(BaseModel):
    answer: str


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """Ask the AegisAI assistant a question about current incidents."""
    from services.chatbot import answer
    return {"answer": answer(req.question)}


# ── WebSocket ─────────────────────────────────────────────────────────────────

@app.websocket("/ws/incidents")
async def ws_incidents(ws: WebSocket):
    """
    Real-time incident feed. On connect, sends the current incident list.
    The server broadcasts updates whenever the incident count changes (≤5 s lag).
    """
    await ws.accept()
    _ws_clients.append(ws)
    try:
        # Push current state immediately on connect
        incidents = get_incidents(limit=100)
        await ws.send_json({
            "type": "incidents",
            "data": [i.model_dump(mode="json") for i in incidents],
        })
        # Keep the connection alive; client can send pings
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=60)
            except asyncio.TimeoutError:
                await ws.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        if ws in _ws_clients:
            _ws_clients.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
