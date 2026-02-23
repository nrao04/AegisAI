from contextlib import asynccontextmanager
from typing import List
from fastapi import FastAPI

from store import get_all_incidents
from schemas import Incident


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start Kafka consumer in background when API starts; stop on shutdown."""
    import asyncio
    from services.log_consumer import run_consumer

    task = asyncio.create_task(run_consumer())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(lifespan=lifespan)


@app.get("/")
def read_root():
    return {"message": "Welcome to AegisAI – AI-Powered Incident Response System"}


@app.get("/incidents", response_model=List[Incident])
def list_incidents():
    """List all incidents (in-memory for Phase 2)."""
    return get_all_incidents()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)