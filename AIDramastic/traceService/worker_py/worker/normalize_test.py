"""normalize_test.py — normalize 配对单测。"""

from __future__ import annotations

from worker.normalize import normalize_batch, normalize_item


def test_level_upper_and_msg_alias():
    got = normalize_item(
        {
            "trace_id": "t1",
            "service": "gateway",
            "level": "info",
            "msg": "hello",
            "timestamp": "2026-09-27T22:00:00+08:00",
        }
    )
    assert got is not None
    assert got["level"] == "INFO"
    assert got["message"] == "hello"
    assert "msg" not in got


def test_missing_trace_id():
    assert normalize_item({"service": "s", "level": "INFO", "message": "m", "timestamp": "t"}) is None


def test_batch_filters():
    items = [
        {"trace_id": "t", "service": "s", "level": "warn", "message": "ok", "timestamp": "t"},
        {"service": "bad"},
    ]
    out = normalize_batch(items)
    assert len(out) == 1
    assert out[0]["level"] == "WARN"
