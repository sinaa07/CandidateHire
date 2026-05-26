#!/usr/bin/env python3
"""CHECK 1: Skill map builds on job creation."""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import requests

COMPANY_ID = "93aa39dc-cef9-4dfc-9419-589a59a71827"
API_KEY = "ca44a0de-99c1-49d2-9c9a-2f60e0c7b299"
BASE = "http://127.0.0.1:8000"
HEADERS = {"X-Company-API-Key": API_KEY}

JD_TEXT = """
Senior Backend Engineer — Acme Corp

We are hiring a Senior Backend Engineer to design and operate scalable services
that power our hiring platform. You will work with product and data teams to
deliver reliable APIs, improve performance, and mentor junior engineers.

Responsibilities:
- Design and implement REST and event-driven services in Python
- Build and maintain PostgreSQL schemas, queries, and migrations
- Deploy services on AWS using Docker and CI/CD pipelines
- Collaborate on system design, code reviews, and incident response
- Integrate LLM-powered features with careful evaluation and monitoring
- Write clear technical documentation and runbooks

Requirements:
- 5+ years of professional software engineering experience
- Strong Python skills (FastAPI or Django preferred)
- Experience with relational databases (PostgreSQL, MySQL)
- Familiarity with cloud infrastructure (AWS, GCP, or Azure)
- Solid understanding of distributed systems and API design
- Excellent communication and cross-functional collaboration

Nice to have:
- Kubernetes, Terraform, or infrastructure-as-code experience
- Background in search, ranking, or machine learning systems
- Experience with observability stacks (Datadog, Prometheus, Grafana)
- Prior work in HR tech, recruiting, or marketplace products

We offer competitive compensation, remote-friendly work, and growth opportunities.
""".strip()


def fail(msg: str) -> None:
    print(f"FAIL: {msg}")
    sys.exit(1)


def main() -> None:
    # Health
    try:
        r = requests.get(f"{BASE}/health", timeout=5)
        r.raise_for_status()
    except Exception as exc:
        fail(f"API not reachable at {BASE}: {exc}")

    # Create job
    form = {
        "title": "E2E Contextual Verify Job",
        "department": "Engineering",
        "status": "open",
        "jd_text": JD_TEXT,
        "ranking_mode": "contextual",
    }
    r = requests.post(
        f"{BASE}/api/v2/companies/{COMPANY_ID}/jobs/",
        headers=HEADERS,
        data=form,
        timeout=30,
    )
    if r.status_code != 201:
        fail(f"Job create returned {r.status_code}: {r.text}")
    job = r.json()
    job_id = job["id"]
    print(f"Created job: {job_id}")

    # Immediate status
    status_url = f"{BASE}/api/v2/companies/{COMPANY_ID}/jobs/{job_id}/pipeline/skill-map/status"
    r = requests.get(status_url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        fail(f"skill-map/status returned {r.status_code}: {r.text}")
    st = r.json()
    print(f"Immediate status: {st.get('status')}")
    if st.get("status") not in ("building", "ready"):
        fail(f"Expected building or ready, got {st.get('status')} error={st.get('error')}")

    # Poll until ready (max 60s)
    deadline = time.time() + 60
    while time.time() < deadline:
        r = requests.get(status_url, headers=HEADERS, timeout=10)
        st = r.json()
        status = st.get("status")
        print(f"  poll: {status}")
        if status == "ready":
            elapsed = 60 - (deadline - time.time())
            print(f"Ready in ~{elapsed:.0f}s poll window")
            break
        if status == "failed":
            fail(f"skill_map_error={st.get('error')}")
        time.sleep(2)
    else:
        fail("Timed out waiting for skill map ready (60s)")

    # GET skill-map
    map_url = f"{BASE}/api/v2/companies/{COMPANY_ID}/jobs/{job_id}/pipeline/skill-map"
    r = requests.get(map_url, headers=HEADERS, timeout=10)
    if r.status_code != 200:
        fail(f"skill-map returned {r.status_code}: {r.text}")
    data = r.json()
    skill_map = data.get("skill_implied_by_map", {})
    if len(skill_map) < 5:
        fail(f"Expected >=5 JD skills, got {len(skill_map)}")
    short = [k for k, v in skill_map.items() if not isinstance(v, list) or len(v) < 5]
    if short:
        fail(f"Skills with <5 implied: {short[:3]}")
    print(f"skill-map OK: {len(skill_map)} skills")

    # File on disk
    path = Path(f"storage/companies/{COMPANY_ID}/jobs/{job_id}/skill_maps/implied_by_map.json")
    if not path.exists():
        fail(f"Missing file: {path}")
    with path.open() as f:
        disk = json.load(f)
    if not isinstance(disk, dict) or len(disk) < 5:
        fail("On-disk implied_by_map.json invalid or too small")
    print(f"File OK: {path}")
    print("CHECK 1 PASSED")
    print(f"JOB_ID={job_id}")


if __name__ == "__main__":
    main()
