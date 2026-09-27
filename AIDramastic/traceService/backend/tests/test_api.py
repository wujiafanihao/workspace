"""test_api.py — health / ingest / query 集成（fakeredis）。"""

from __future__ import annotations

import aiosqlite
import pytest


@pytest.mark.asyncio
async def test_healthz(api_client):
    client, _, _ = api_client
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ingest_enqueue_only(api_client):
    client, fake, db_path = api_client
    body = {
        "logs": [
            {
                "trace_id": "11111111-1111-1111-1111-111111111111",
                "service": "gateway",
                "level": "INFO",
                "message": "hi",
                "timestamp": "2026-09-27T22:00:00+08:00",
            }
        ]
    }
    r = await client.post("/api/v1/logs/ingest", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["code"] == 0
    assert data["data"]["accepted"] == 1
    assert await fake.xlen("trace:ingest") == 1
    # 确认未写入 sqlite
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute("SELECT COUNT(*) FROM logs")
        (count,) = await cur.fetchone()
        assert count == 0


@pytest.mark.asyncio
async def test_ingest_msg_alias(api_client):
    client, _, _ = api_client
    body = {
        "logs": [
            {
                "trace_id": "t",
                "service": "gateway",
                "level": "INFO",
                "msg": "alias",
                "timestamp": "2026-09-27T22:00:00+08:00",
            }
        ]
    }
    r = await client.post("/api/v1/logs/ingest", json=body)
    assert r.status_code == 200
    assert r.json()["data"]["accepted"] == 1


@pytest.mark.asyncio
async def test_query_missing_param(api_client):
    client, _, _ = api_client
    r = await client.get("/api/v1/logs")
    assert r.status_code == 400
    assert r.json()["code"] == 40001


@pytest.mark.asyncio
async def test_query_empty(api_client):
    client, _, _ = api_client
    r = await client.get("/api/v1/logs", params={"trace_id": "nope"})
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["logs"] == []


@pytest.mark.asyncio
async def test_query_from_sqlite(api_client):
    client, _, db_path = api_client
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO logs (trace_id, service, level, message, timestamp, fields_json) VALUES (?,?,?,?,?,?)",
            ("tid-q", "gateway", "INFO", "row", "2026-09-27T22:00:00+08:00", "{}"),
        )
        await db.commit()
    r = await client.get("/api/v1/logs", params={"trace_id": "tid-q"})
    assert r.status_code == 200
    logs = r.json()["data"]["logs"]
    assert len(logs) == 1
    assert logs[0]["message"] == "row"
