"""redis_client.py — 异步 Redis 连接池封装。

负责：启动时规范化创建 redis.asyncio 连接池；提供 get/close。
不负责：业务入队/缓存语义（见 services/queue.py、cache.py）。
依赖：redis.asyncio；config.RedisConfig。
"""

from __future__ import annotations

from typing import Optional

import redis.asyncio as aioredis

from app.config import RedisConfig
from app.logger import get_logger

log = get_logger(__name__)

_pool: Optional[aioredis.Redis] = None


def _redis_url(cfg: RedisConfig) -> str:
    """由 addr/password 拼 redis URL。"""
    host, _, port = cfg.addr.partition(":")
    port = port or "6379"
    if cfg.password:
        return f"redis://:{cfg.password}@{host}:{port}/0"
    return f"redis://{host}:{port}/0"


async def init_redis(cfg: RedisConfig) -> aioredis.Redis:
    """初始化全局 Redis 连接池。

    入参：cfg Redis 配置。出参：asyncio Redis 客户端。
    副作用：创建连接池；替换模块级 _pool。
    """
    global _pool
    url = _redis_url(cfg)
    _pool = aioredis.from_url(
        url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=20,
        socket_connect_timeout=2.0,
        socket_timeout=2.0,
    )
    log.info("redis pool initialized", extra={"fields": {"addr": cfg.addr}})
    return _pool


async def close_redis() -> None:
    """关闭全局 Redis 连接池。

    副作用：aclose 池；清空 _pool。
    """
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        log.info("redis pool closed")


def get_redis() -> aioredis.Redis:
    """获取已初始化的 Redis 客户端；未初始化则抛 RuntimeError。"""
    if _pool is None:
        raise RuntimeError("redis pool not initialized")
    return _pool


async def ping_redis() -> bool:
    """探测 Redis 是否可用；失败返回 False 不抛。"""
    try:
        r = get_redis()
        return bool(await r.ping())
    except Exception:
        return False
