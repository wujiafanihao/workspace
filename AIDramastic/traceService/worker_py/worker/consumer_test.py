"""consumer_test.py — process_stream_messages / claim_count / ACK 语义离线单测。"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from worker.config import NormalizeCfg, RedisCfg, WorkerConfig
from worker.consumer import Consumer, process_stream_messages, processing_key


def _good_payload(**overrides: object) -> str:
    base = {
        "trace_id": "t1",
        "service": "s",
        "level": "info",
        "message": "ok",
        "timestamp": "ts",
    }
    base.update(overrides)
    return json.dumps(base)


def test_process_stream_messages_filters_bad_keeps_ids():
    messages = [
        ("1-0", {"payload": _good_payload()}),
        ("2-0", {"payload": "not-json"}),
        ("3-0", {"payload": _good_payload(trace_id="t2")}),
        ("4-0", {"payload": json.dumps({"service": "only"})}),
    ]
    batch, persist_ids, discard_ids = process_stream_messages(messages)
    assert persist_ids == ["1-0", "3-0"]
    assert discard_ids == ["2-0", "4-0"]
    assert len(batch) == 2
    assert batch[0]["trace_id"] == "t1"
    assert batch[0]["level"] == "INFO"
    assert batch[1]["trace_id"] == "t2"


def test_process_stream_messages_empty():
    batch, persist_ids, discard_ids = process_stream_messages([])
    assert batch == []
    assert persist_ids == []
    assert discard_ids == []


def test_claim_count_defaults_to_max_batch():
    cfg = WorkerConfig(
        redis=RedisCfg(claim_count=0),
        normalize=NormalizeCfg(max_batch=42),
    )
    c = Consumer(cfg)
    assert c.claim_count() == 42
    c.cfg.redis.claim_count = 7
    assert c.claim_count() == 7


def test_processing_key():
    assert processing_key("trace:ingest") == "trace:ingest:processing"
    assert processing_key("q") == "q:processing"


@pytest.mark.asyncio
async def test_ingest_and_ack_skips_ack_when_enqueue_fails():
    """enqueue_persist 失败时不得 ACK 有效条目；毒丸仍可 ACK。"""
    cfg = WorkerConfig(
        redis=RedisCfg(
            ingest_queue_key="trace:ingest",
            group="g",
            queue_type="stream",
        ),
        normalize=NormalizeCfg(max_batch=10),
    )
    c = Consumer(cfg)
    client = AsyncMock()
    messages = [
        ("1-0", {"payload": _good_payload()}),
        ("2-0", {"payload": "not-json"}),
        ("3-0", {"payload": _good_payload(trace_id="t2")}),
    ]

    with patch(
        "worker.consumer.enqueue_persist",
        new_callable=AsyncMock,
        side_effect=ConnectionError("persist enqueue failed"),
    ) as mock_enqueue:
        with pytest.raises(ConnectionError, match="persist enqueue failed"):
            await c._ingest_and_ack(client, messages)

    mock_enqueue.assert_awaited_once()
    # 毒丸 2-0 已 ACK；有效 1-0/3-0 未 ACK
    assert client.xack.await_count == 1
    ack_args = client.xack.await_args.args
    assert ack_args[0] == "trace:ingest"
    assert ack_args[1] == "g"
    assert set(ack_args[2:]) == {"2-0"}


@pytest.mark.asyncio
async def test_ingest_and_ack_acks_after_successful_enqueue():
    """enqueue_persist 成功后 ACK 有效 id；毒丸也 ACK。"""
    cfg = WorkerConfig(
        redis=RedisCfg(
            ingest_queue_key="trace:ingest",
            group="g",
            queue_type="stream",
        ),
        normalize=NormalizeCfg(max_batch=10),
    )
    c = Consumer(cfg)
    client = AsyncMock()
    messages = [
        ("1-0", {"payload": _good_payload()}),
        ("2-0", {"payload": "not-json"}),
    ]

    with patch(
        "worker.consumer.enqueue_persist",
        new_callable=AsyncMock,
        return_value=1,
    ) as mock_enqueue:
        await c._ingest_and_ack(client, messages)

    mock_enqueue.assert_awaited_once()
    assert client.xack.await_count == 2
    first_ack = set(client.xack.await_args_list[0].args[2:])
    second_ack = set(client.xack.await_args_list[1].args[2:])
    assert first_ack == {"2-0"}
    assert second_ack == {"1-0"}


@pytest.mark.asyncio
async def test_consume_list_skips_lrem_when_enqueue_fails():
    """list 路径：enqueue_persist 失败时不 LREM processing。"""
    cfg = WorkerConfig(
        redis=RedisCfg(
            ingest_queue_key="trace:ingest",
            queue_type="list",
        ),
        normalize=NormalizeCfg(max_batch=10),
    )
    c = Consumer(cfg)
    client = AsyncMock()
    raw = _good_payload()
    client.blmove = AsyncMock(return_value=raw)

    with patch(
        "worker.consumer.enqueue_persist",
        new_callable=AsyncMock,
        side_effect=RuntimeError("persist down"),
    ):
        with pytest.raises(RuntimeError, match="persist down"):
            await c._consume_list(client)

    client.lrem.assert_not_awaited()


@pytest.mark.asyncio
async def test_consume_list_lrem_poison_without_enqueue():
    """list 毒丸（坏 JSON）直接 LREM，不入 persist。"""
    cfg = WorkerConfig(
        redis=RedisCfg(
            ingest_queue_key="trace:ingest",
            queue_type="list",
        ),
        normalize=NormalizeCfg(max_batch=10),
    )
    c = Consumer(cfg)
    client = AsyncMock()
    raw = "not-json{{"
    client.blmove = AsyncMock(return_value=raw)

    with patch(
        "worker.consumer.enqueue_persist",
        new_callable=AsyncMock,
    ) as mock_enqueue:
        await c._consume_list(client)

    mock_enqueue.assert_not_awaited()
    client.lrem.assert_awaited_once_with("trace:ingest:processing", 1, raw)
