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
    副作用：pipeline XADD/LPUSH；超 soft_limit 抛 BizError(50301)；Redis 异常同码。

    批量入队走 Redis pipeline，减少往返并尽量一次落地。pipeline execute
    失败时 Redis 侧仍可能已写入部分条目（at-least-once，非 MULTI 事务语义），
    因此不返回部分成功 HTTP；客户端须容忍重复、消费者须幂等（stream 侧
    persist 已有 redis_msg_id）。失败时 BizError.data 带 enqueued_before_error
    供观测（execute 未返回时为 0，实际落库数可能 >0）。
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
        # transaction=False：一次往返批量发出；非 MULTI/EXEC，失败仍可能部分写入。
        pipe = client.pipeline(transaction=False)
        if cfg.queue_type == "list":
            for item in items:
                payload = json.dumps(item, ensure_ascii=False)
                pipe.lpush(key, payload)
        else:
            for item in items:
                # Stream：整条 JSON 放 payload 字段，便于跨语言消费
                pipe.xadd(
                    key,
                    {"payload": json.dumps(item, ensure_ascii=False)},
                    maxlen=cfg.stream_maxlen,
                    approximate=True,
                )
        results = await pipe.execute()
        accepted = len(results) if results is not None else len(items)
    except BizError:
        raise
    except Exception as exc:
        log.error(
            "enqueue failed",
            extra={
                "fields": {
                    "err": str(exc),
                    "enqueued_before_error": accepted,
                    "attempted": len(items),
                }
            },
        )
        raise BizError(
            ErrorCode.QUEUE_UNAVAILABLE,
            message="enqueue failed",
            data={"enqueued_before_error": accepted, "attempted": len(items)},
        ) from exc

    return accepted
