"""producer_test.py — enqueue_persist MAXLEN 配对测试。"""

from __future__ import annotations

import pytest
import fakeredis.aioredis

from worker.config import RedisCfg
from worker.producer import enqueue_persist


@pytest.fixture
async def fake_redis():
    r = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield r
    await r.aclose()


@pytest.mark.asyncio
async def test_enqueue_persist_passes_maxlen(fake_redis, monkeypatch):
    cfg = RedisCfg(
        queue_type="stream",
        persist_queue_key="trace:persist",
        stream_maxlen=55,
    )
    calls: list[dict] = []
    real_xadd = fake_redis.xadd

    async def spy_xadd(*args, **kwargs):
        calls.append({"args": args, "kwargs": kwargs})
        return await real_xadd(*args, **kwargs)

    monkeypatch.setattr(fake_redis, "xadd", spy_xadd)
    n = await enqueue_persist(
        fake_redis,
        cfg,
        [{"trace_id": "t1", "service": "s", "level": "INFO", "message": "m", "timestamp": "t"}],
    )
    assert n == 1
    assert len(calls) == 1
    assert calls[0]["kwargs"].get("maxlen") == 55
    assert calls[0]["kwargs"].get("approximate") is True


@pytest.mark.asyncio
async def test_enqueue_persist_maxlen_trims(fake_redis):
    cfg = RedisCfg(
        queue_type="stream",
        persist_queue_key="trace:persist",
        stream_maxlen=3,
    )
    for i in range(8):
        await enqueue_persist(
            fake_redis,
            cfg,
            [{"trace_id": f"t{i}", "service": "s", "level": "INFO", "message": "m", "timestamp": "t"}],
        )
    assert await fake_redis.xlen("trace:persist") <= 3


def test_redis_cfg_stream_maxlen_default():
    from worker.constants import DEFAULT_STREAM_MAXLEN

    assert RedisCfg().stream_maxlen == DEFAULT_STREAM_MAXLEN
