"""
Elasticsearch integration for incidents (Phase 5).

Assumes a local or remote Elasticsearch node is reachable at
ELASTICSEARCH_URL (default: http://localhost:9200).

Environment variables:
  - ELASTICSEARCH_URL: full URL to the ES node
  - ELASTICSEARCH_INDEX: index name (default: "incidents")
"""

import logging
import os
import time
from typing import List

from elasticsearch import Elasticsearch

from schemas import Incident

logger = logging.getLogger(__name__)

ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = os.getenv("ELASTICSEARCH_INDEX", "incidents")

_client: Elasticsearch | None = None

# ES 8.x mapping for incidents index
INCIDENT_MAPPINGS = {
    "properties": {
        "id": {"type": "keyword"},
        "title": {"type": "text"},
        "severity": {"type": "keyword"},
        "source": {"type": "keyword"},
        "tenant": {"type": "keyword"},
        "raw_log": {"type": "text"},
        "created_at": {"type": "date"},
        "status": {"type": "keyword"},
    }
}


def _get_client() -> Elasticsearch:
    global _client
    if _client is None:
        _client = Elasticsearch(ELASTICSEARCH_URL)
    return _client


def init_index() -> None:
    """
    Create the incidents index with a simple mapping if it does not exist.

    Retries a few times so that when running in Docker, ES has time to become ready.
    Safe to call multiple times.
    """
    max_attempts = 5
    for attempt in range(1, max_attempts + 1):
        try:
            es = _get_client()
            if es.indices.exists(index=INDEX_NAME):
                logger.info("Elasticsearch index %s already exists", INDEX_NAME)
                return
            # ES 8.x client: use mappings= (not body=)
            es.indices.create(index=INDEX_NAME, mappings=INCIDENT_MAPPINGS)
            logger.info("Elasticsearch index %s created", INDEX_NAME)
            return
        except Exception as e:
            logger.warning(
                "Elasticsearch init_index attempt %s/%s failed: %s (url=%s)",
                attempt,
                max_attempts,
                e,
                ELASTICSEARCH_URL,
            )
            if attempt == max_attempts:
                logger.error(
                    "Elasticsearch index creation failed after %s attempts; search will fall back to DB.",
                    max_attempts,
                )
                return
            time.sleep(2)


def index_incident(incident: Incident) -> None:
    """Index a single incident document in Elasticsearch."""
    try:
        es = _get_client()
        try:
            doc = incident.model_dump(mode="json")
        except AttributeError:
            doc = incident.dict()
        es.index(index=INDEX_NAME, id=incident.id, document=doc)
    except Exception as e:
        logger.warning("Elasticsearch index_incident failed for id=%s: %s", incident.id, e)


def search_incidents(query: str, limit: int = 50) -> List[Incident]:
    """
    Search incidents by query string across title, raw_log, severity, and source.

    Returns an empty list if Elasticsearch is unavailable.
    Uses ES 8.x API: query= and size= (not body=).
    """
    try:
        es = _get_client()
        # ES 8.x: pass query and size as top-level params
        resp = es.search(
            index=INDEX_NAME,
            query={
                "multi_match": {
                    "query": query,
                    "fields": ["title", "raw_log", "severity", "source", "tenant"],
                }
            },
            size=limit,
        )
        hits = resp.get("hits", {}).get("hits", [])
        out = []
        for hit in hits:
            src = hit["_source"]
            src.setdefault("tenant", "default")
            out.append(Incident(**src))
        return out
    except Exception as e:
        logger.warning("Elasticsearch search_incidents failed: %s (url=%s)", e, ELASTICSEARCH_URL)
        return []

