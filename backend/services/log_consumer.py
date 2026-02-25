"""
Kafka consumer for the logs topic. Creates an incident per message, stores in Postgres,
indexes in Elasticsearch. Uses deterministic IDs (partition+offset) for idempotency and
commits offsets only after both writes succeed (at-least-once).
"""
import asyncio
import hashlib
import logging
import os
import re
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


def _tenant_from_log(raw_log: str) -> str:
    """Extract tenant from log if present (e.g. tenant=acme or tenant:acme), else default."""
    m = re.search(r"tenant[=:](\w+)", raw_log, re.IGNORECASE)
    return m.group(1).lower() if m else "default"


def _log_to_incident(msg_value: bytes, partition: int, offset: int) -> Incident:
    """Build an incident with a deterministic id so retries don't create duplicates."""
    raw_log = msg_value.decode("utf-8", errors="replace").strip()
    title = raw_log[:80] + ("..." if len(raw_log) > 80 else "")
    severity = "high" if "error" in raw_log.lower() else "medium"
    tenant = _tenant_from_log(raw_log)
    # Deterministic id: same partition+offset+content => same id (idempotent retries)
    id_digest = hashlib.sha256(
        f"{partition}_{offset}_{msg_value!r}".encode()
    ).hexdigest()[:32]
    return Incident(
        id=id_digest,
        title=title,
        severity=severity,
        source="kafka",
        tenant=tenant,
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
            enable_auto_commit=False,
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
                incident = _log_to_incident(msg.value, msg.partition, msg.offset)
                insert_incident(incident)
                index_incident(incident)
                await consumer.commit()
                logger.info(
                    "Incident created, stored, indexed, offset committed: id=%s tenant=%s title=%r",
                    incident.id,
                    incident.tenant,
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
