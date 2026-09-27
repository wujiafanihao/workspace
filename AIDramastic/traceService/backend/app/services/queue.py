"""queue.py — Redis 入队封装（trace:ingest）。

负责：异步 XADD（stream）或 LPUSH（list）；软上限 XLEN/LLEN → BizError 50301。
不负责：消费、规范化、SQLite。
依赖：redis.asyncio；errors.BizError；config.RedisConfig。
"""

from __future__ import annotations

import json
from typing import Any

import redis.asyncio as aioredis

from app.config import RedisConfig
from app.errors import BizError, ErrorCode
from app.logger import get_logger

log = get_logger(__name__)


async def queue_depth(client: aioredis.Redis, cfg: RedisConfig) -> int:
    """查询 ingest 队列深度（XLEN 或 LLEN）。"""
    key = cfg.ingest_queue_key
    if cfg.queue_type == "list":
        return int(await client.llen(key))
    return int(await client.xlen(key))


async def enqueue_logs(
    client: aioredis.Redis,
    cfg: RedisConfig,
    items: list[dict[str, Any]],
) -> int:
    """将日志条目异步入队到 trace:ingest。

    入参：client Redis；cfg 队列配置；items 已校验字典列表。
    出参：成功入队条数。
    副作用：XADD/LPUSH；超 soft_limit 抛 BizError(50301)；Redis 异常同码。
    """
    if not items:
        return 0
    try:
        depth = await queue_depth(client, cfg)
        if depth >= cfg.queue_soft_limit:
            log.error(
                "queue soft limit reached",
                extra={
                    "fields": {
                        "depth": depth,
                        "limit": cfg.queue_soft_limit,
                        "code": ErrorCode.QUEUE_UNAVAILABLE,
                    }
                },
            )
            raise BizError(ErrorCode.QUEUE_UNAVAILABLE)
    except BizError:
        raise
    except Exception as exc:
        log.error("redis depth check failed", extra={"fields": {"err": str(exc)}})
        raise BizError(ErrorCode.QUEUE_UNAVAILABLE, message="redis unavailable") from exc

    accepted = 0
    key = cfg.ingest_queue_key
    try:
        if cfg.queue_type == "list":
            for item in items:
                payload = json.dumps(item, ensure_ascii=False)
                await client.lpush(key, payload)
                accepted += 1
        else:
            for item in items:
                # Stream：整条 JSON 放 payload 字段，便于跨语言消费
                await client.xadd(
                    key,
                    {"payload": json.dumps(item, ensure_ascii=False)},
                )
                accepted += 1
    except BizError:
        raise
    except Exception as exc:
        log.error("enqueue failed", extra={"fields": {"err": str(exc)}})
        raise BizError(ErrorCode.QUEUE_UNAVAILABLE, message="enqueue failed") from exc

    return accepted
