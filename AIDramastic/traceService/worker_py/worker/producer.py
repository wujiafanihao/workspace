"""producer.py — 写入 trace:persist。

负责：XADD/LPUSH 规范化后的条目。
不负责：消费 ingest；写 SQLite。
依赖：redis.asyncio。
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from worker.config import RedisCfg
from worker.log import get_logger

log = get_logger(__name__)


async def enqueue_persist(
    client: aioredis.Redis,
    cfg: RedisCfg,
    items: list[dict[str, Any]],
) -> int:
    """将规范化日志写入 persist 队列。出参：写入条数。"""
    n = 0
    key = cfg.persist_queue_key
    for item in items:
        payload = json.dumps(item, ensure_ascii=False)
        if cfg.queue_type == "list":
            await client.lpush(key, payload)
        else:
            await client.xadd(key, {"payload": payload})
        n += 1
        log.info("enqueued persist", extra={"trace_id": item.get("trace_id")})
    return n
