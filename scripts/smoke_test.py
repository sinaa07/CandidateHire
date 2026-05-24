#!/usr/bin/env python3
"""
End-to-end smoke test for CandidateHire v2 API.

Usage:
  DISABLE_AUTH=true uvicorn app.main:app --reload   # in another terminal
  python scripts/smoke_test.py

Environment:
  SMOKE_TEST_URL   Base URL (default http://127.0.0.1:8000)
  DISABLE_AUTH     If true on server, API key header is optional
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

API_BASE = os.getenv("SMOKE_TEST_URL", "http://127.0.0.1:8000").rstrip("/")
RESUME_DIR = Path(__file__).parent / "test_resumes"
INDEX_TIMEOUT_SEC = int(os.getenv("SMOKE_INDEX_TIMEOUT", "120"))
POLL_INTERVAL_SEC = 2

SAMPLE_JD = """
Senior Backend Engineer — Python / FastAPI

We are hiring a backend engineer to build scalable APIs and data services.

Requirements:
- 4+ years Python development
- FastAPI or Django REST experience
- PostgreSQL and Redis
- Docker and CI/CD
- Machine learning exposure is a plus

Nice to have: React, AWS, Kubernetes, NLP, PyTorch
""".strip()


class StepResult:
    def __init__(self, name: str, passed: bool, elapsed_ms: float, detail: str = ""):
        self.name = name
        self.passed = passed
        self.elapsed_ms = elapsed_ms
        self.detail = detail


def _headers(api_key: str | None) -> dict[str, str]:
    if api_key:
        return {"X-Company-API-Key": api_key}
    return {}


def _run_step(name: str, fn) -> StepResult:
    start = time.perf_counter()
    try:
        detail = fn()
        elapsed = (time.perf_counter() - start) * 1000
        return StepResult(name, True, elapsed, detail or "")
    except Exception as exc:
        elapsed = (time.perf_counter() - start) * 1000
        return StepResult(name, False, elapsed, str(exc))


def main() -> int:
    results: list[StepResult] = []
    state: dict[str, str] = {}

    print(f"Smoke test target: {API_BASE}\n")

    # Step 1: Create company
    def step1():
        slug = f"smoke-{int(time.time())}"
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/",
            json={"name": "Smoke Test Co", "slug": slug},
            timeout=30.0,
        )
        if r.status_code != 201:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        state["company_id"] = data["id"]
        state["api_key"] = data["api_key"]
        return f"company_id={state['company_id']}"

    results.append(_run_step("1. Create company", step1))
    if not results[-1].passed:
        _print_results(results)
        return 1

    api_key = state["api_key"]
    company_id = state["company_id"]
    auth = _headers(api_key)

    # Step 2: Create job
    def step2():
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/",
            data={
                "title": "Senior Backend Engineer",
                "department": "Engineering",
                "status": "open",
                "jd_text": SAMPLE_JD,
            },
            headers=auth,
            timeout=30.0,
        )
        if r.status_code != 201:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        state["job_id"] = r.json()["id"]
        return f"job_id={state['job_id']}"

    results.append(_run_step("2. Create job", step2))
    if not results[-1].passed:
        _print_results(results)
        return 1

    job_id = state["job_id"]

    # Step 3: Upload resumes
    def step3():
        files = []
        for path in sorted(RESUME_DIR.glob("*.txt")):
            files.append(
                ("files", (path.name, path.read_bytes(), "text/plain")),
            )
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/resumes/",
            files=files,
            headers=auth,
            timeout=60.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        if data.get("uploaded") != 3:
            raise RuntimeError(f"expected uploaded=3, got {json.dumps(data)}")
        return f"uploaded={data['uploaded']}"

    results.append(_run_step("3. Upload 3 resumes", step3))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 4: Trigger indexing
    def step4():
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/pipeline/index",
            headers=auth,
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        if data.get("queued") != 3:
            raise RuntimeError(f"expected queued=3, got {json.dumps(data)}")
        return f"queued={data['queued']}"

    results.append(_run_step("4. Trigger indexing", step4))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 5: Poll status
    def step5():
        deadline = time.time() + INDEX_TIMEOUT_SEC
        last = {}
        while time.time() < deadline:
            r = httpx.get(
                f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/pipeline/status",
                headers=auth,
                timeout=15.0,
            )
            if r.status_code != 200:
                raise RuntimeError(f"status {r.status_code}: {r.text}")
            last = r.json()
            if last.get("indexing_complete"):
                return (
                    f"processed={last.get('processed')} failed={last.get('failed')} "
                    f"duplicate={last.get('duplicate')}"
                )
            time.sleep(POLL_INTERVAL_SEC)
        raise RuntimeError(f"timeout after {INDEX_TIMEOUT_SEC}s, last={json.dumps(last)}")

    results.append(_run_step("5. Poll indexing status", step5))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 6: Rank
    def step6():
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/pipeline/rank",
            headers=auth,
            timeout=120.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        if data.get("ranked_count", 0) < 1:
            raise RuntimeError(f"expected ranked_count>=1, got {json.dumps(data)}")
        state["ranked_count"] = str(data.get("ranked_count"))
        return f"ranked_count={data.get('ranked_count')}"

    results.append(_run_step("6. Trigger ranking", step6))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 7: GET rankings
    def step7():
        r = httpx.get(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/pipeline/rankings",
            params={"limit": 50},
            headers=auth,
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        items = data.get("items", [])
        if len(items) < 1:
            raise RuntimeError(f"expected rankings, got {json.dumps(data)}")
        for item in items:
            if (item.get("final_score") or 0) <= 0 and item.get("passed_hard_filter"):
                raise RuntimeError(f"expected final_score > 0 for passed filter: {item}")
        return f"results={len(items)}"

    results.append(_run_step("7. GET rankings", step7))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 8: Rerank
    def step8():
        r = httpx.post(
            f"{API_BASE}/api/v2/companies/{company_id}/jobs/{job_id}/pipeline/rerank",
            headers=auth,
            json={
                "weights": {
                    "semantic": 0.25,
                    "skill_match": 0.25,
                    "experience": 0.25,
                    "education": 0.25,
                }
            },
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        if len(data) < 1:
            raise RuntimeError(f"expected rerank results, got {data}")
        return f"reranked={len(data)}"

    results.append(_run_step("8. Rerank", step8))
    if not results[-1].passed:
        _print_results(results)
        return 1

    # Step 9: Dashboard
    def step9():
        r = httpx.get(
            f"{API_BASE}/api/v2/companies/{company_id}/dashboard",
            headers=auth,
            timeout=30.0,
        )
        if r.status_code != 200:
            raise RuntimeError(f"status {r.status_code}: {r.text}")
        data = r.json()
        summary = data.get("summary", {})
        if summary.get("total_jobs", 0) < 1:
            raise RuntimeError(f"expected total_jobs>=1, got {json.dumps(summary)}")
        if summary.get("total_candidates", 0) != 3:
            raise RuntimeError(f"expected total_candidates=3, got {json.dumps(summary)}")
        return json.dumps(summary)

    results.append(_run_step("9. GET dashboard", step9))

    _print_results(results)
    failed = sum(1 for r in results if not r.passed)
    if failed:
        print(f"\n{failed} step(s) FAILED")
        return 1
    print("\nAll steps PASSED")
    print(f"\ncompany_id={company_id}")
    print(f"api_key={api_key}")
    print(f"job_id={job_id}")
    return 0


def _print_results(results: list[StepResult]) -> None:
    print()
    for r in results:
        status = "PASS" if r.passed else "FAIL"
        print(f"[{status}] {r.name} ({r.elapsed_ms:.0f}ms)")
        if r.detail:
            print(f"       {r.detail}")


if __name__ == "__main__":
    sys.exit(main())
