"""consumer.py — 消费 trace:ingest（XREADGROUP / BRPOP）。

负责：确保消费者组、循环读取、ACK、调用 normalize + producer。
不负责：写 SQLite。
依赖：redis.asyncio；normalize；producer。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import redis.asyncio as aioredis

from worker.config import WorkerConfig
from worker.log import get_logger
from worker.normalize import normalize_item
from worker.producer import enqueue_persist

log = get_logger(__name__)


def _redis_url(cfg: WorkerConfig) -> str:
    host, _, port = cfg.redis.addr.partition(":")
    port = port or "6379"
    if cfg.redis.password:
        return f"redis://:{cfg.redis.password}@{host}:{port}/0"
    return f"redis://{host}:{port}/0"


async def ensure_group(client: aioredis.Redis, cfg: WorkerConfig) -> None:
    """创建 Stream 消费者组（已存在则忽略）。"""
    if cfg.redis.queue_type != "stream":
        return
    try:
        await client.xgroup_create(
            cfg.redis.ingest_queue_key,
            cfg.redis.group,
            id="0",
            mkstream=True,
        )
        log.info("consumer group created")
    except Exception as exc:
        msg = str(exc)
        if "BUSYGROUP" in msg or "already exists" in msg.lower():
            return
        raise


class Consumer:
    """可优雅停止的 ingest 消费者。"""

    def __init__(self, cfg: WorkerConfig) -> None:
        self.cfg = cfg
        self._stop = asyncio.Event()
        self._client: aioredis.Redis | None = None

    def request_stop(self) -> None:
        """响应 SIGINT/SIGTERM。"""
        self._stop.set()

    async def run(self) -> None:
        """主循环：消费 → 规范化 → 入 persist。禁止写 SQLite。"""
        self._client = aioredis.from_url(
            _redis_url(self.cfg),
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=5.0,
        )
        client = self._client
        await ensure_group(client, self.cfg)
        log.info("worker_py started")
        try:
            while not self._stop.is_set():
                try:
                    if self.cfg.redis.queue_type == "list":
                        await self._consume_list(client)
                    else:
                        await self._consume_stream(client)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    log.error(f"consume loop error: {exc}")
                    await asyncio.sleep(0.5)
        finally:
            await client.aclose()
            log.info("worker_py stopped")

    async def _consume_stream(self, client: aioredis.Redis) -> None:
        """XREADGROUP 一批。"""
        rows = await client.xreadgroup(
            groupname=self.cfg.redis.group,
            consumername=self.cfg.redis.consumer,
            streams={self.cfg.redis.ingest_queue_key: ">"},
            count=self.cfg.normalize.max_batch,
            block=max(self.cfg.normalize.flush_interval_ms, 50),
        )
        if not rows:
            return
        batch: list[dict[str, Any]] = []
        ids: list[str] = []
        for _stream, messages in rows:
            for msg_id, fields in messages:
                raw = fields.get("payload") or "{}"
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {}
                norm = normalize_item(data) if isinstance(data, dict) else None
                if norm:
                    batch.append(norm)
                ids.append(msg_id)
        if batch:
            await enqueue_persist(client, self.cfg.redis, batch)
        if ids:
            await client.xack(self.cfg.redis.ingest_queue_key, self.cfg.redis.group, *ids)

    async def _consume_list(self, client: aioredis.Redis) -> None:
        """BRPOP 单条（简化）。"""
        item = await client.brpop(self.cfg.redis.ingest_queue_key, timeout=1)
        if not item:
            await asyncio.sleep(0.05)
            return
        _key, raw = item
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return
        norm = normalize_item(data) if isinstance(data, dict) else None
        if norm:
            await enqueue_persist(client, self.cfg.redis, [norm])
