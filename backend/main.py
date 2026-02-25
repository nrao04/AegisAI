from typing import List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from db import get_incident, get_incidents
from schemas import Incident
from services.search import search_incidents


app = FastAPI()


@app.get("/")
def read_root():
    return {"message": "Welcome to AegisAI – AI-Powered Incident Response System"}


@app.get("/incidents", response_model=List[Incident])
def list_incidents(limit: int = 100):
    """List incidents from PostgreSQL, most recent first."""
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")
    return get_incidents(limit=limit)


@app.get("/incidents/{incident_id}", response_model=Incident)
def read_incident(incident_id: str):
    """Get a single incident by ID."""
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


class IncidentStatusUpdate(BaseModel):
    status: str = Field(..., description="New status, e.g. open, acknowledged, resolved")

@app.get("/incidents/search", response_model=List[Incident])
def search_incidents_endpoint(q: str, limit: int = 50):
    """
    Full-text search over incidents using Elasticsearch.

    Falls back to an empty list if Elasticsearch is unavailable.
    """
    if limit <= 0:
        raise HTTPException(status_code=400, detail="limit must be positive")
    return search_incidents(query=q, limit=limit)

@app.patch("/incidents/{incident_id}", response_model=Incident)
def update_incident_status(incident_id: str, payload: IncidentStatusUpdate):
    """
    Update the status of an incident.

    For example: open -> acknowledged -> resolved.
    """
    incident = get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    incident.status = payload.status

    # Persist the change by re-inserting/upserting the incident.
    from db import insert_incident

    insert_incident(incident)
    return incident


@app.post("/incidents", response_model=Incident)
def create_incident(incident: Incident):
    """
    Create an incident manually.

    Useful for testing the API without going through Kafka.
    """
    from db import insert_incident

    insert_incident(incident)
    return incident


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)