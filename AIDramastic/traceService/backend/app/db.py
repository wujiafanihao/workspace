"""db.py — SQLite 只读访问（aiosqlite）。

负责：query 用只读连接；本地 ensure_schema 便于单测/联调。
不负责：日志主路径写入（生产由 Go Worker 拥有写锁）。
依赖：aiosqlite；DESIGN §4 DDL。

说明：ensure_schema 仅在 API 启动时创建空表结构，便于 query 测试；
生产环境表结构与 WAL 由 Go Worker 维护，API 不得 INSERT/UPDATE/DELETE logs。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import aiosqlite

from app.constants import SQLITE_BUSY_TIMEOUT_MS
from app.logger import get_logger

log = get_logger(__name__)

DDL = """
CREATE TABLE IF NOT EXISTS logs (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id      TEXT    NOT NULL,
  span_id       TEXT,
  service       TEXT    NOT NULL,
  level         TEXT    NOT NULL,
  message       TEXT    NOT NULL,
  timestamp     TEXT    NOT NULL,
  fields_json   TEXT,
  redis_msg_id  TEXT,
  created_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_logs_trace_ts ON logs(trace_id, timestamp);
CREATE UNIQUE INDEX IF NOT EXISTS idx_logs_redis_msg_id ON logs(redis_msg_id);
"""


async def ensure_schema(db_path: str) -> None:
    """确保 logs 表与索引存在（仅建表，非业务写入路径）。

    入参：db_path SQLite 文件路径。
    副作用：创建父目录与表；生产写路径仍属 Go Worker。
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        await db.executescript(DDL)
        # 旧库补列；列已存在时忽略
        try:
            await db.execute("ALTER TABLE logs ADD COLUMN redis_msg_id TEXT")
        except Exception:
            pass
        await db.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_logs_redis_msg_id ON logs(redis_msg_id)"
        )
        await db.commit()
    log.info("sqlite schema ensured (read-side)", extra={"fields": {"path": db_path}})


async def fetch_logs_by_trace_id(db_path: str, trace_id: str) -> list[dict[str, Any]]:
    """按 trace_id 查询日志，按 timestamp ASC。

    入参：db_path、trace_id。出参：字典列表（含解析后的 fields）。
    副作用：只读 SELECT；无写。
    """
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    # 只读 URI：生产避免 API 意外写入；若文件不存在先 ensure
    if not Path(db_path).exists():
        await ensure_schema(db_path)

    rows: list[dict[str, Any]] = []
    async with aiosqlite.connect(db_path) as db:
        await db.execute(f"PRAGMA busy_timeout={SQLITE_BUSY_TIMEOUT_MS}")
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, trace_id, span_id, service, level, message, timestamp, fields_json
            FROM logs
            WHERE trace_id = ?
            ORDER BY timestamp ASC
            """,
            (trace_id,),
        )
        for row in await cursor.fetchall():
            fields: dict[str, Any] = {}
            raw = row["fields_json"]
            if raw:
                try:
                    parsed = json.loads(raw)
                    if isinstance(parsed, dict):
                        fields = parsed
                except json.JSONDecodeError:
                    fields = {}
            rows.append(
                {
                    "id": row["id"],
                    "trace_id": row["trace_id"],
                    "span_id": row["span_id"],
                    "service": row["service"],
                    "level": row["level"],
                    "message": row["message"],
                    "timestamp": row["timestamp"],
                    "fields": fields,
                }
            )
    return rows
