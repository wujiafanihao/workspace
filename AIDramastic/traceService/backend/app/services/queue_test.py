"""queue_test.py — queue.enqueue_logs 配对测试（fakeredis）。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest
import fakeredis.aioredis

from app.config import RedisConfig
from app.errors import BizError, ErrorCode
from app.services import queue as queue_svc


@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.mark.asyncio
async def test_enqueue_stream_xadd(fake_redis):
    cfg = RedisConfig(queue_type="stream", ingest_queue_key="trace:ingest", queue_soft_limit=100)
    items = [
        {
            "trace_id": "t1",
            "service": "gateway",
            "level": "INFO",
            "message": "hi",
            "timestamp": "2026-09-27T22:00:00+08:00",
            "fields": {},
        }
    ]
    n = await queue_svc.enqueue_logs(fake_redis, cfg, items)
    assert n == 1
    assert await fake_redis.xlen("trace:ingest") == 1
    entries = await fake_redis.xrange("trace:ingest")
    payload = json.loads(entries[0][1]["payload"])
    assert payload["trace_id"] == "t1"


@pytest.mark.asyncio
async def test_enqueue_list_lpush(fake_redis):
    cfg = RedisConfig(queue_type="list", ingest_queue_key="trace:ingest", queue_soft_limit=100)
    items = [{"trace_id": "t2", "service": "s", "level": "INFO", "message": "m", "timestamp": "t", "fields": {}}]
    n = await queue_svc.enqueue_logs(fake_redis, cfg, items)
    assert n == 1
    assert await fake_redis.llen("trace:ingest") == 1


@pytest.mark.asyncio
async def test_soft_limit_raises_50301(fake_redis):
    cfg = RedisConfig(queue_type="stream", ingest_queue_key="trace:ingest", queue_soft_limit=1)
    await fake_redis.xadd("trace:ingest", {"payload": "{}"})
    with pytest.raises(BizError) as ei:
        await queue_svc.enqueue_logs(
            fake_redis,
            cfg,
            [{"trace_id": "t", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}}],
        )
    assert ei.value.code == ErrorCode.QUEUE_UNAVAILABLE


@pytest.mark.asyncio
async def test_enqueue_stream_passes_maxlen(fake_redis, monkeypatch):
    """stream 入队必须带 approximate MAXLEN，避免 XLEN 只增不减。"""
    cfg = RedisConfig(
        queue_type="stream",
        ingest_queue_key="trace:ingest",
        queue_soft_limit=100,
        stream_maxlen=42,
    )
    calls: list[dict] = []
    real_pipeline = fake_redis.pipeline

    def spy_pipeline(*args, **kwargs):
        pipe = real_pipeline(*args, **kwargs)
        real_xadd = pipe.xadd

        def spy_xadd(*a, **kw):
            calls.append({"args": a, "kwargs": kw})
            return real_xadd(*a, **kw)

        pipe.xadd = spy_xadd
        return pipe

    monkeypatch.setattr(fake_redis, "pipeline", spy_pipeline)
    n = await queue_svc.enqueue_logs(
        fake_redis,
        cfg,
        [{"trace_id": "t", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}}],
    )
    assert n == 1
    assert len(calls) == 1
    assert calls[0]["kwargs"].get("maxlen") == 42
    assert calls[0]["kwargs"].get("approximate") is True


@pytest.mark.asyncio
async def test_enqueue_stream_maxlen_trims(fake_redis):
    """approximate MAXLEN 生效后流长度受上限约束（fakeredis 精确裁剪亦可）。"""
    cfg = RedisConfig(
        queue_type="stream",
        ingest_queue_key="trace:ingest",
        queue_soft_limit=1000,
        stream_maxlen=3,
    )
    for i in range(10):
        await queue_svc.enqueue_logs(
            fake_redis,
            cfg,
            [{"trace_id": f"t{i}", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}}],
        )
    assert await fake_redis.xlen("trace:ingest") <= 3


@pytest.mark.asyncio
async def test_enqueue_uses_pipeline_batch(fake_redis, monkeypatch):
    """批量入队应走 pipeline（一次 execute），而非逐条 await。"""
    cfg = RedisConfig(queue_type="stream", ingest_queue_key="trace:ingest", queue_soft_limit=100)
    items = [
        {"trace_id": f"t{i}", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}}
        for i in range(3)
    ]
    pipeline_calls: list[dict] = []
    execute_calls: list[int] = []
    real_pipeline = fake_redis.pipeline

    def spy_pipeline(*args, **kwargs):
        pipeline_calls.append({"args": args, "kwargs": kwargs})
        pipe = real_pipeline(*args, **kwargs)
        real_execute = pipe.execute

        async def spy_execute(*a, **kw):
            execute_calls.append(1)
            return await real_execute(*a, **kw)

        pipe.execute = spy_execute
        return pipe

    monkeypatch.setattr(fake_redis, "pipeline", spy_pipeline)
    n = await queue_svc.enqueue_logs(fake_redis, cfg, items)
    assert n == 3
    assert len(pipeline_calls) == 1
    assert pipeline_calls[0]["kwargs"].get("transaction") is False
    assert len(execute_calls) == 1
    assert await fake_redis.xlen("trace:ingest") == 3


@pytest.mark.asyncio
async def test_enqueue_pipeline_failure_raises_with_enqueued_before_error(fake_redis, monkeypatch):
    """pipeline execute 失败时抛 QUEUE_UNAVAILABLE，data 含 enqueued_before_error。"""
    cfg = RedisConfig(queue_type="list", ingest_queue_key="trace:ingest", queue_soft_limit=100)
    items = [
        {"trace_id": "t1", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}},
        {"trace_id": "t2", "service": "s", "level": "I", "message": "m", "timestamp": "t", "fields": {}},
    ]

    real_pipeline = fake_redis.pipeline

    def boom_pipeline(*args, **kwargs):
        pipe = real_pipeline(*args, **kwargs)

        async def fail_execute(*a, **kw):
            raise ConnectionError("redis down mid-pipeline")

        pipe.execute = fail_execute
        return pipe

    monkeypatch.setattr(fake_redis, "pipeline", boom_pipeline)
    with pytest.raises(BizError) as ei:
        await queue_svc.enqueue_logs(fake_redis, cfg, items)
    assert ei.value.code == ErrorCode.QUEUE_UNAVAILABLE
    assert ei.value.data is not None
    assert ei.value.data.get("enqueued_before_error") == 0
    assert ei.value.data.get("attempted") == 2
