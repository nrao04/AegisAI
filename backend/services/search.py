"""
Elasticsearch integration for incidents (Phase 5).

Assumes a local or remote Elasticsearch node is reachable at
ELASTICSEARCH_URL (default: http://localhost:9200).

Environment variables:
  - ELASTICSEARCH_URL: full URL to the ES node
  - ELASTICSEARCH_INDEX: index name (default: "incidents")
"""

import os
from typing import List

from elasticsearch import Elasticsearch

from schemas import Incident


ELASTICSEARCH_URL = os.getenv("ELASTICSEARCH_URL", "http://localhost:9200")
INDEX_NAME = os.getenv("ELASTICSEARCH_INDEX", "incidents")

_client: Elasticsearch | None = None


def _get_client() -> Elasticsearch:
    global _client
    if _client is None:
        _client = Elasticsearch(ELASTICSEARCH_URL)
    return _client


def init_index() -> None:
    """
    Create the incidents index with a simple mapping if it does not exist.

    Safe to call multiple times.
    """
    try:
        es = _get_client()
        if es.indices.exists(index=INDEX_NAME):
            return
        es.indices.create(
            index=INDEX_NAME,
            body={
                "mappings": {
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
            },
        )
    except Exception:
        # Fail silently in Phase 5; API will still work with PostgreSQL only.
        return


def index_incident(incident: Incident) -> None:
    """Index a single incident document in Elasticsearch."""
    try:
        es = _get_client()
        try:
            doc = incident.model_dump(mode="json")
        except AttributeError:
            doc = incident.dict()
        es.index(index=INDEX_NAME, id=incident.id, document=doc)
    except Exception:
        # Swallow indexing errors for now; they shouldn't break ingestion.
        return


def search_incidents(query: str, limit: int = 50) -> List[Incident]:
    """
    Search incidents by query string across title, raw_log, severity, and source.

    Returns an empty list if Elasticsearch is unavailable.
    """
    try:
        es = _get_client()
        body = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "raw_log", "severity", "source", "tenant"],
                }
            }
        }
        resp = es.search(index=INDEX_NAME, body=body, size=limit)
        hits = resp.get("hits", {}).get("hits", [])
        out = []
        for hit in hits:
            src = hit["_source"]
            src.setdefault("tenant", "default")
            out.append(Incident(**src))
        return out
    except Exception:
        return []

