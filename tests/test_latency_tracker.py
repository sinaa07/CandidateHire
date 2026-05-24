"""Tests for latency percentile and aggregation."""
import json
from pathlib import Path

from app.utils.latency_tracker import (
    LatencyRecorder,
    percentile,
    save_latency_report,
    summarize_samples,
    STAGE_OCR,
    STAGE_PARSING,
)


def test_percentile_empty():
    assert percentile([], 50) is None


def test_percentile_single():
    assert percentile([42.0], 95) == 42.0


def test_percentile_p50():
    values = [10.0, 20.0, 30.0, 40.0, 50.0]
    p50 = percentile(values, 50)
    assert p50 is not None
    assert 20.0 <= p50 <= 30.0


def test_summarize_samples():
    stats = summarize_samples([100.0, 200.0, 300.0, 400.0, 500.0])
    assert stats["count"] == 5
    assert stats["mean_ms"] == 300.0
    assert stats["p50_ms"] is not None
    assert stats["p95_ms"] is not None
    assert stats["p99_ms"] is not None


def test_recorder_stage_context_manager():
    recorder = LatencyRecorder()
    with recorder.stage(STAGE_PARSING):
        pass
    assert STAGE_PARSING in recorder.to_samples_dict()
    assert len(recorder.to_samples_dict()[STAGE_PARSING]) == 1


def test_recorder_merge():
    a = LatencyRecorder()
    b = LatencyRecorder()
    a.record(STAGE_OCR, 10.0)
    b.record(STAGE_OCR, 20.0)
    a.merge(b)
    summary = a.summary()
    assert summary["stages"][STAGE_OCR]["count"] == 2


def test_save_latency_report(tmp_path):
    recorder = LatencyRecorder()
    recorder.record(STAGE_OCR, 15.5)
    recorder.record(STAGE_OCR, 25.0)
    path = save_latency_report(tmp_path, recorder, label="test")
    assert path.exists()
    data = json.loads(path.read_text())
    assert data["label"] == "test"
    assert "ocr" in data["stages"]
    assert data["stages"]["ocr"]["p50_ms"] is not None
