"""queue_test.py — queue.enqueue_logs 配对测试（fakeredis）。"""

from __future__ import annotations

import json

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
