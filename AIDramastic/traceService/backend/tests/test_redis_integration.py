"""test_redis_integration.py — 若本机 127.0.0.1:6379 可用则跑真实 Redis 入队。"""

from __future__ import annotations

import socket

import pytest
import redis.asyncio as aioredis

from app.config import RedisConfig
from app.services import queue as queue_svc


def _redis_up(host: str = "127.0.0.1", port: int = 6379) -> bool:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _redis_up(), reason="redis not available on 127.0.0.1:6379")


@pytest.mark.asyncio
async def test_real_redis_enqueue():
    client = aioredis.from_url("redis://127.0.0.1:6379/15", decode_responses=True)
    key = "trace:ingest:pytest"
    try:
        await client.delete(key)
        cfg = RedisConfig(queue_type="stream", ingest_queue_key=key, queue_soft_limit=1000)
        n = await queue_svc.enqueue_logs(
            client,
            cfg,
            [
                {
                    "trace_id": "pytest-tid",
                    "service": "pytest",
                    "level": "INFO",
                    "message": "integration",
                    "timestamp": "2026-09-27T22:00:00+08:00",
                    "fields": {},
                }
            ],
        )
        assert n == 1
        assert await client.xlen(key) >= 1
    finally:
        await client.delete(key)
        await client.aclose()
