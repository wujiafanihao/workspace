"""cache.py — 按 trace_id 的查询缓存（JSON SETEX/GET）。

负责：get/setex `trace:{id}`；序列化 list[dict]。
不负责：缓存失效（由 Go Worker DEL）。
依赖：redis.asyncio；config.RedisConfig。
"""

from __future__ import annotations

import json
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import RedisConfig
from app.logger import get_logger

log = get_logger(__name__)


def cache_key(cfg: RedisConfig, trace_id: str) -> str:
    """构造缓存键 trace:{id}。"""
    return f"{cfg.cache_prefix}{trace_id}"


async def get_trace_logs(
    client: aioredis.Redis,
    cfg: RedisConfig,
    trace_id: str,
) -> Optional[list[dict[str, Any]]]:
    """读取缓存；未命中返回 None。

    入参：client、cfg、trace_id。出参：日志 list 或 None。
    副作用：GET；解析失败视为 miss。
    """
    key = cache_key(cfg, trace_id)
    try:
        raw = await client.get(key)
    except Exception as exc:
        log.warning("cache get failed", extra={"fields": {"err": str(exc)}})
        return None
    if raw is None:
        return None
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        log.warning("cache corrupt", extra={"trace_id": trace_id})
    return None


async def set_trace_logs(
    client: aioredis.Redis,
    cfg: RedisConfig,
    trace_id: str,
    logs: list[dict[str, Any]],
) -> None:
    """写入缓存 SETEX。

    入参：logs 可 JSON 序列化列表。副作用：SETEX；失败仅打日志不抛。
    """
    key = cache_key(cfg, trace_id)
    try:
        payload = json.dumps(logs, ensure_ascii=False)
        await client.set(key, payload, ex=cfg.cache_ttl_sec)
    except Exception as exc:
        log.warning("cache set failed", extra={"fields": {"err": str(exc)}})
