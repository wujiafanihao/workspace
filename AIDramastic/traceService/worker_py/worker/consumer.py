"""consumer.py — 消费 trace:ingest（XREADGROUP / XAUTOCLAIM / BRPOP）。

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


def process_stream_messages(
    messages: list[tuple[str, dict[str, Any]]],
) -> tuple[list[dict[str, Any]], list[str]]:
    """将 claim/read 得到的消息解析为 (batch, ids)。

    纯逻辑、不触 Redis，便于单测。非法 payload 仍收集 id（保持现有 ACK-after-enqueue）。
    """
    batch: list[dict[str, Any]] = []
    ids: list[str] = []
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
    return batch, ids


class Consumer:
    """可优雅停止的 ingest 消费者。"""

    def __init__(self, cfg: WorkerConfig) -> None:
        self.cfg = cfg
        self._stop = asyncio.Event()
        self._client: aioredis.Redis | None = None

    def request_stop(self) -> None:
        """响应 SIGINT/SIGTERM。"""
        self._stop.set()

    def claim_count(self) -> int:
        """本轮 XAUTOCLAIM COUNT；未配置 claim_count 时用 max_batch。"""
        if self.cfg.redis.claim_count > 0:
            return self.cfg.redis.claim_count
        return self.cfg.normalize.max_batch

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

    async def _claim_pending(self, client: aioredis.Redis) -> list[tuple[str, dict[str, Any]]]:
        """XAUTOCLAIM 回收空闲 PEL，返回 [(id, fields), ...]。"""
        result = await client.xautoclaim(
            name=self.cfg.redis.ingest_queue_key,
            groupname=self.cfg.redis.group,
            consumername=self.cfg.redis.consumer,
            min_idle_time=self.cfg.redis.claim_min_idle_ms,
            start_id="0-0",
            count=self.claim_count(),
        )
        # redis-py: [next_start_id, messages, deleted_ids?]
        if not result or len(result) < 2:
            return []
        messages = result[1] or []
        return list(messages)

    async def _ingest_and_ack(
        self,
        client: aioredis.Redis,
        messages: list[tuple[str, dict[str, Any]]],
    ) -> None:
        """normalize → enqueue_persist → ACK（保持现有 ACK-after-enqueue 行为）。"""
        if not messages:
            return
        batch, ids = process_stream_messages(messages)
        if batch:
            await enqueue_persist(client, self.cfg.redis, batch)
        if ids:
            await client.xack(self.cfg.redis.ingest_queue_key, self.cfg.redis.group, *ids)

    async def _consume_stream(self, client: aioredis.Redis) -> None:
        """先 XAUTOCLAIM 回收 PEL，再 XREADGROUP 读新消息。"""
        # 先回收崩溃后卡在 PEL 的空闲条目，再读新消息 (">")。
        claimed = await self._claim_pending(client)
        await self._ingest_and_ack(client, claimed)

        rows = await client.xreadgroup(
            groupname=self.cfg.redis.group,
            consumername=self.cfg.redis.consumer,
            streams={self.cfg.redis.ingest_queue_key: ">"},
            count=self.cfg.normalize.max_batch,
            block=max(self.cfg.normalize.flush_interval_ms, 50),
        )
        if not rows:
            return
        fresh: list[tuple[str, dict[str, Any]]] = []
        for _stream, messages in rows:
            fresh.extend(messages)
        await self._ingest_and_ack(client, fresh)

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
