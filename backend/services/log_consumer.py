"""
Kafka consumer for the logs topic. Creates an incident per message and stores in memory.
Run as script: python -m services.log_consumer (from backend/)
Or run alongside the API via FastAPI lifespan (see main.py).
"""
import asyncio
import logging
import os
from datetime import datetime

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from schemas import Incident
from db import insert_incident, init_db
from services.search import init_index, index_incident

BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP", "127.0.0.1:9092")
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
    # Ensure DB schema and search index exist before consuming.
    init_db()
    init_index()

    logger.info("Starting Kafka consumer loop with bootstrap_servers=%s", BOOTSTRAP_SERVERS)

    while True:
        consumer = AIOKafkaConsumer(
            LOGS_TOPIC,
            bootstrap_servers=BOOTSTRAP_SERVERS,
            group_id="aegis-log-consumer",
        )
        try:
            try:
                await consumer.start()
                logger.info("Kafka consumer started, subscribed to topic '%s'", LOGS_TOPIC)
            except KafkaConnectionError as e:
                logger.warning("Kafka not ready (%s); retrying in 5s", e)
                await asyncio.sleep(5)
                continue

            async for msg in consumer:
                incident = _log_to_incident(msg.value)
                insert_incident(incident)
                # Best-effort indexing into Elasticsearch.
                index_incident(incident)
                logger.info(
                    "Incident created, stored, and indexed: id=%s title=%r",
                    incident.id,
                    incident.title,
                )
        except Exception as e:
            logger.exception("Error in Kafka consumer loop; restarting in 5s: %s", e)
            await asyncio.sleep(5)
        finally:
            try:
                await consumer.stop()
            except Exception:
                pass


if __name__ == "__main__":
    asyncio.run(run_consumer())
