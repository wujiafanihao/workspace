"""consumer_test.py — process_stream_messages / claim_count 离线单测。"""

from __future__ import annotations

import json

from worker.config import NormalizeCfg, RedisCfg, WorkerConfig
from worker.consumer import Consumer, process_stream_messages


def _good_payload(**overrides: object) -> str:
    base = {
        "trace_id": "t1",
        "service": "s",
        "level": "info",
        "message": "ok",
        "timestamp": "ts",
    }
    base.update(overrides)
    return json.dumps(base)


def test_process_stream_messages_filters_bad_keeps_ids():
    messages = [
        ("1-0", {"payload": _good_payload()}),
        ("2-0", {"payload": "not-json"}),
        ("3-0", {"payload": _good_payload(trace_id="t2")}),
        ("4-0", {"payload": json.dumps({"service": "only"})}),
    ]
    batch, ids = process_stream_messages(messages)
    assert ids == ["1-0", "2-0", "3-0", "4-0"]
    assert len(batch) == 2
    assert batch[0]["trace_id"] == "t1"
    assert batch[0]["level"] == "INFO"
    assert batch[1]["trace_id"] == "t2"


def test_process_stream_messages_empty():
    batch, ids = process_stream_messages([])
    assert batch == []
    assert ids == []


def test_claim_count_defaults_to_max_batch():
    cfg = WorkerConfig(
        redis=RedisCfg(claim_count=0),
        normalize=NormalizeCfg(max_batch=42),
    )
    c = Consumer(cfg)
    assert c.claim_count() == 42
    c.cfg.redis.claim_count = 7
    assert c.claim_count() == 7
