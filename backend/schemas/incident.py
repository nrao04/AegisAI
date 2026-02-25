from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field


class Incident(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str = ""
    severity: str = "unknown"  # e.g. low, medium, high, critical
    source: str = "kafka"
    tenant: str = "default"  # customer/tenant scope — "which customers are affected"
    raw_log: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: str = "open"  # open, acknowledged, resolved
