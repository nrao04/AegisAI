"""
Kafka consumer for the logs topic. Creates an incident per message and stores in memory.
Run as script: python -m services.log_consumer (from backend/)
Or run alongside the API via FastAPI lifespan (see main.py).
"""
from aiokafka import AIOKafkaConsumer
from datetime import datetime
import asyncio
import logging

from schemas import Incident
from store import add_incident

BOOTSTRAP_SERVERS = "127.0.0.1:9092"
LOGS_TOPIC = "logs"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _log_to_incident(raw_bytes: bytes) -> Incident:
    raw_log = raw_bytes.decode("utf-8", errors="replace").strip()
    title = raw_log[:80] + ("..." if len(raw_log) > 80 else "")
    severity = "high" if "error" in raw_log.lower() else "medium"
    return Incident(
        title=title,
        severity=severity,
        source="kafka",
        raw_log=raw_log,
        created_at=datetime.utcnow(),
        status="open",
    )


async def run_consumer():
    consumer = AIOKafkaConsumer(
        LOGS_TOPIC,
        bootstrap_servers=BOOTSTRAP_SERVERS,
        group_id="aegis-log-consumer",
    )
    await consumer.start()
    try:
        async for msg in consumer:
            incident = _log_to_incident(msg.value)
            add_incident(incident)
            logger.info("Incident created: id=%s title=%r", incident.id, incident.title)
    finally:
        await consumer.stop()


if __name__ == "__main__":
    asyncio.run(run_consumer())
