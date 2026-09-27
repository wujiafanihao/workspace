"""cache_test.py — cache get/setex 配对测试。"""

from __future__ import annotations

import pytest
import fakeredis.aioredis

from app.config import RedisConfig
from app.services import cache as cache_svc


@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.mark.asyncio
async def test_set_and_get(fake_redis):
    cfg = RedisConfig(cache_prefix="trace:", cache_ttl_sec=60)
    logs = [{"trace_id": "tid", "service": "g", "level": "INFO", "message": "m", "timestamp": "t", "fields": {}}]
    await cache_svc.set_trace_logs(fake_redis, cfg, "tid", logs)
    got = await cache_svc.get_trace_logs(fake_redis, cfg, "tid")
    assert got == logs


@pytest.mark.asyncio
async def test_miss_returns_none(fake_redis):
    cfg = RedisConfig(cache_prefix="trace:", cache_ttl_sec=60)
    assert await cache_svc.get_trace_logs(fake_redis, cfg, "missing") is None
