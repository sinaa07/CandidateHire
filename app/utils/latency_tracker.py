"""Per-stage latency measurement with p50 / p95 / p99 aggregation."""
from __future__ import annotations

import json
import time
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, DefaultDict, Iterator, Optional

# Canonical stage names used across the pipeline
STAGE_TEXT_EXTRACTION = "text_extraction"
STAGE_OCR = "ocr"
STAGE_PARSING = "parsing"
STAGE_CHUNKING = "chunking"
STAGE_EMBEDDING_GENERATION = "embedding_generation"
STAGE_NER = "ner"
STAGE_LLM = "llm"
STAGE_DB_WRITES = "db_writes"

ALL_STAGES = (
    STAGE_TEXT_EXTRACTION,
    STAGE_OCR,
    STAGE_PARSING,
    STAGE_CHUNKING,
    STAGE_EMBEDDING_GENERATION,
    STAGE_NER,
    STAGE_LLM,
    STAGE_DB_WRITES,
)


def percentile(values: list[float], p: float) -> Optional[float]:
    """Linear-interpolation percentile (p in 0–100)."""
    if not values:
        return None
    sorted_v = sorted(values)
    if len(sorted_v) == 1:
        return round(sorted_v[0], 3)
    k = (len(sorted_v) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_v) - 1)
    if f == c:
        return round(sorted_v[f], 3)
    return round(sorted_v[f] + (sorted_v[c] - sorted_v[f]) * (k - f), 3)


def summarize_samples(samples: list[float]) -> dict[str, Any]:
    """Compute latency stats for a list of duration samples (milliseconds)."""
    if not samples:
        return {
            "count": 0,
            "mean_ms": None,
            "min_ms": None,
            "max_ms": None,
            "p50_ms": None,
            "p95_ms": None,
            "p99_ms": None,
        }
    return {
        "count": len(samples),
        "mean_ms": round(sum(samples) / len(samples), 3),
        "min_ms": round(min(samples), 3),
        "max_ms": round(max(samples), 3),
        "p50_ms": percentile(samples, 50),
        "p95_ms": percentile(samples, 95),
        "p99_ms": percentile(samples, 99),
    }


class LatencyRecorder:
    """Collects per-stage duration samples in milliseconds."""

    def __init__(self) -> None:
        self._samples: DefaultDict[str, list[float]] = defaultdict(list)

    def record(self, stage: str, duration_ms: float) -> None:
        if duration_ms >= 0:
            self._samples[stage].append(duration_ms)

    @contextmanager
    def stage(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start) * 1000
            self.record(name, elapsed_ms)

    def merge(self, other: LatencyRecorder) -> None:
        for stage, samples in other._samples.items():
            self._samples[stage].extend(samples)

    def merge_samples(self, samples: dict[str, list[float]]) -> None:
        for stage, values in samples.items():
            self._samples[stage].extend(values)

    def to_samples_dict(self) -> dict[str, list[float]]:
        return {stage: list(values) for stage, values in self._samples.items()}

    def summary(self, label: str = "pipeline") -> dict[str, Any]:
        """Build a JSON-serializable latency report."""
        stages: dict[str, Any] = {}
        for stage_name in ALL_STAGES:
            stats = summarize_samples(self._samples.get(stage_name, []))
            if stats["count"] > 0:
                stages[stage_name] = stats
        # Include any ad-hoc stages not in ALL_STAGES
        for stage_name, samples in self._samples.items():
            if stage_name not in stages and samples:
                stages[stage_name] = summarize_samples(samples)

        total_samples = sum(len(v) for v in self._samples.values())
        return {
            "label": label,
            "generated_at": datetime.now(UTC).isoformat(),
            "total_samples": total_samples,
            "stages": stages,
        }


def _samples_sidecar_path(reports_dir: Path) -> Path:
    return reports_dir / "latency_samples.json"


def load_samples_sidecar(reports_dir: Path) -> dict[str, list[float]]:
    path = _samples_sidecar_path(reports_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def save_latency_report(
    reports_dir: Path,
    recorder: LatencyRecorder,
    label: str = "pipeline",
    filename: str = "latency_report.json",
    merge_existing: bool = True,
) -> Path:
    """Persist latency summary; optionally merge with prior samples sidecar."""
    reports_dir.mkdir(parents=True, exist_ok=True)
    combined = LatencyRecorder()
    if merge_existing:
        combined.merge_samples(load_samples_sidecar(reports_dir))
    combined.merge(recorder)
    # Update cumulative raw samples for accurate percentiles across runs
    all_samples = combined.to_samples_dict()
    _samples_sidecar_path(reports_dir).write_text(
        json.dumps(all_samples, indent=2), encoding="utf-8"
    )
    report_path = reports_dir / filename
    report = combined.summary(label=label)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report_path


def load_latency_report(reports_dir: Path, filename: str = "latency_report.json") -> Optional[dict]:
    path = reports_dir / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def merge_latency_reports(*reports: dict) -> dict:
    """Merge multiple latency report summaries by re-aggregating raw stats is not possible;
    merge sample lists from recorders instead. This merges stage stats by weighted average
    when only summaries are available (used for combining phase labels)."""
    merged_recorder = LatencyRecorder()
    for report in reports:
        if not report:
            continue
        for stage_name, stats in report.get("stages", {}).items():
            count = stats.get("count", 0)
            mean = stats.get("mean_ms")
            if count and mean is not None:
                # Approximate: duplicate mean for each count (lossy but preserves totals)
                merged_recorder._samples[stage_name].extend([mean] * count)
    return merged_recorder.summary(label="merged")
