"""consumer.py — 消费 trace:ingest（XREADGROUP / XAUTOCLAIM / BLMOVE list）。

负责：确保消费者组、循环读取、ACK/LREM、调用 normalize + producer。
不负责：写 SQLite。
依赖：redis.asyncio；normalize；producer。
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from urllib.parse import quote

import redis.asyncio as aioredis

from worker.config import WorkerConfig
from worker.log import get_logger
from worker.normalize import normalize_item
from worker.producer import enqueue_persist

log = get_logger(__name__)



def processing_key(queue_key: str) -> str:
    """可靠 list 队列的 processing 侧键：queue_key + ":processing"。"""
    return f"{queue_key}:processing"


def _redis_url(cfg: WorkerConfig) -> str:
    host, _, port = cfg.redis.addr.partition(":")
    port = port or "6379"
    if cfg.redis.password:
        return f"redis://:{quote(cfg.redis.password, safe='')}@{host}:{port}/0"
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
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """将 claim/read 得到的消息解析为 (batch, persist_ids, discard_ids)。

    纯逻辑、不触 Redis，便于单测。
    - batch / persist_ids：规范化成功，仅在 enqueue_persist 成功后 ACK。
    - discard_ids：坏 JSON / normalize 为空（毒丸），可立即 ACK 丢弃。
    """
    batch: list[dict[str, Any]] = []
    persist_ids: list[str] = []
    discard_ids: list[str] = []
    for msg_id, fields in messages:
        raw = fields.get("payload") or "{}"
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            data = {}
        norm = normalize_item(data) if isinstance(data, dict) else None
        if norm:
            batch.append(norm)
            persist_ids.append(msg_id)
        else:
            discard_ids.append(msg_id)
    return batch, persist_ids, discard_ids


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
        if self.cfg.redis.queue_type == "list":
            await self._requeue_processing(client)
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
        """normalize → enqueue_persist → ACK。

        毒丸（discard_ids）立即 ACK；有效条目仅在 enqueue_persist 成功后 ACK。
        enqueue_persist 失败时不 ACK persist_ids，留给 PEL/XAUTOCLAIM 重试。
        """
        if not messages:
            return
        batch, persist_ids, discard_ids = process_stream_messages(messages)
        key = self.cfg.redis.ingest_queue_key
        group = self.cfg.redis.group
        if discard_ids:
            await client.xack(key, group, *discard_ids)
        if not batch:
            return
        await enqueue_persist(client, self.cfg.redis, batch)
        # 仅成功入 persist 后 ACK；失败则抛错、不 ACK。
        if persist_ids:
            await client.xack(key, group, *persist_ids)

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

    async def _requeue_processing(self, client: aioredis.Redis) -> None:
        """将 processing 中未完成项全部回队到主 list（崩溃恢复）。"""
        src = self.cfg.redis.ingest_queue_key
        pk = processing_key(src)
        while True:
            moved = await client.rpoplpush(pk, src)
            if moved is None:
                return

    async def _move_to_processing(self, client: aioredis.Redis) -> str | None:
        """原子地从主 list 移到 processing（BLMOVE；未知命令回退 BRPOPLPUSH）。"""
        src = self.cfg.redis.ingest_queue_key
        dst = processing_key(src)
        try:
            return await client.blmove(src, dst, timeout=1, src="RIGHT", dest="LEFT")
        except Exception as exc:
            msg = str(exc).lower()
            if "unknown command" in msg or "err unknown" in msg:
                return await client.brpoplpush(src, dst, timeout=1)
            raise

    async def _consume_list(self, client: aioredis.Redis) -> None:
        """BLMOVE/BRPOPLPUSH 到 processing；enqueue_persist 成功后才 LREM。

        坏 JSON / normalize 为空：视为毒丸，直接 LREM 丢弃。
        enqueue_persist 失败：不 LREM，留在 processing 供启动回队重试。
        """
        raw = await self._move_to_processing(client)
        if not raw:
            await asyncio.sleep(0.05)
            return
        dst = processing_key(self.cfg.redis.ingest_queue_key)
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            await client.lrem(dst, 1, raw)
            return
        norm = normalize_item(data) if isinstance(data, dict) else None
        if not norm:
            # 毒丸：丢弃
            await client.lrem(dst, 1, raw)
            return
        await enqueue_persist(client, self.cfg.redis, [norm])
        # 仅成功入 persist 后从 processing 移除
        await client.lrem(dst, 1, raw)
