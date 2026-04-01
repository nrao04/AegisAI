"""
Demo seed script for AegisAI.

Populates the system with realistic-looking incidents across multiple tenants,
severities, and statuses so the dashboard is meaningful when demoing or screenshotting.

Usage (with the stack running):
    python seed.py
    python seed.py --base http://localhost:8000
"""

import argparse
import sys
import time
import urllib.request
import urllib.error
import json

LOGS = [
    # HIGH / critical
    ("CRITICAL: PostgreSQL primary node unreachable, failover initiated (tenant=acme)", "postgres-monitor"),
    ("ERROR: Payment service latency p99 > 8000ms — SLO breach (tenant=acme)", "latency-monitor"),
    ("ERROR: Redis cache cluster eviction rate 94% — OOM imminent (tenant=globex)", "redis-monitor"),
    ("ERROR: Kubernetes pod CrashLoopBackOff — api-gateway deployment (tenant=globex)", "k8s-controller"),
    ("ERROR: SSL certificate expires in 2 days — api.acme.io (tenant=acme)", "cert-monitor"),

    # MEDIUM
    ("WARNING: Disk usage at 87% on /dev/sda1 node-3 (tenant=acme)", "disk-monitor"),
    ("WARNING: Background job queue depth 1,240 — processing delayed (tenant=globex)", "queue-monitor"),
    ("WARNING: Elasticsearch heap usage at 78% — GC pressure increasing (tenant=acme)", "es-monitor"),
    ("WARNING: Auth service returning elevated 401 rate (tenant=globex)", "auth-monitor"),

    # LOW
    ("INFO: Scheduled maintenance window starting in 30 minutes (tenant=acme)", "ops-scheduler"),
    ("INFO: Deployment pipeline completed — staging environment (tenant=globex)", "ci-runner"),
]

# Incidents to resolve or acknowledge after creation (by index into LOGS)
ACKNOWLEDGE = {2, 4, 7}
RESOLVE     = {1, 9, 10}


def post(base: str, path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def patch(base: str, path: str, body: dict) -> dict:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="PATCH",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def main(base: str) -> None:
    # Wait for the backend to be ready
    for attempt in range(10):
        try:
            with urllib.request.urlopen(f"{base}/health", timeout=3):
                break
        except Exception:
            if attempt == 9:
                print(f"Backend not reachable at {base} after 10 attempts. Is it running?")
                sys.exit(1)
            print(f"  waiting for backend... ({attempt + 1}/10)")
            time.sleep(2)

    print(f"Seeding {len(LOGS)} incidents into {base}\n")

    ids = []
    for i, (log_line, source) in enumerate(LOGS):
        try:
            inc = post(base, "/ingest", {"log": log_line, "source": source})
            ids.append(inc["id"])
            status_marker = ""
            if i in RESOLVE:
                status_marker = " -> resolved"
            elif i in ACKNOWLEDGE:
                status_marker = " -> acknowledged"
            print(f"  [{inc['severity'].upper():8}] {inc['title'][:60]}{status_marker}")
        except Exception as e:
            print(f"  FAILED ({log_line[:50]}): {e}")
            ids.append(None)

    # Update statuses
    for i, inc_id in enumerate(ids):
        if inc_id is None:
            continue
        try:
            if i in RESOLVE:
                patch(base, f"/incidents/{inc_id}", {"status": "resolved"})
            elif i in ACKNOWLEDGE:
                patch(base, f"/incidents/{inc_id}", {"status": "acknowledged"})
        except Exception as e:
            print(f"  Status update failed for {inc_id}: {e}")

    print(f"\nDone. Open http://localhost:3000 to see the dashboard.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed AegisAI with demo incidents.")
    parser.add_argument("--base", default="http://localhost:8000", help="API base URL")
    args = parser.parse_args()
    main(args.base.rstrip("/"))
