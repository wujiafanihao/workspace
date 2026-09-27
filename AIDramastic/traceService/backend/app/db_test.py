"""db_test.py — 只读 query 与 ensure_schema。"""

from __future__ import annotations

import aiosqlite
import pytest

from app.db import ensure_schema, fetch_logs_by_trace_id


@pytest.mark.asyncio
async def test_fetch_empty(tmp_path):
    db_path = str(tmp_path / "logs.db")
    await ensure_schema(db_path)
    rows = await fetch_logs_by_trace_id(db_path, "no-such")
    assert rows == []


@pytest.mark.asyncio
async def test_fetch_ordered(tmp_path):
    db_path = str(tmp_path / "logs.db")
    await ensure_schema(db_path)
    async with aiosqlite.connect(db_path) as db:
        # 测试夹具写入：模拟 Go Worker；生产 API 路径禁止写
        await db.execute(
            "INSERT INTO logs (trace_id, service, level, message, timestamp, fields_json) VALUES (?,?,?,?,?,?)",
            ("tid", "b", "INFO", "second", "2026-09-27T22:00:02+08:00", "{}"),
        )
        await db.execute(
            "INSERT INTO logs (trace_id, service, level, message, timestamp, fields_json) VALUES (?,?,?,?,?,?)",
            ("tid", "a", "INFO", "first", "2026-09-27T22:00:01+08:00", "{}"),
        )
        await db.commit()
    rows = await fetch_logs_by_trace_id(db_path, "tid")
    assert [r["message"] for r in rows] == ["first", "second"]
