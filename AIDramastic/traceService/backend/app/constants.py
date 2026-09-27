"""constants.py — 服务级常量集中封装。

负责：HTTP 业务成功码、默认 Redis/服务名等不可热更常量。
不负责：可 YAML 热更的超时/池大小/地址（见 config.py）。
依赖：无。
"""

from __future__ import annotations

# 统一响应成功码
CODE_OK: int = 0
MSG_OK: str = "ok"

# 服务标识（结构化日志 service 字段）
SERVICE_NAME: str = "trace-api"

# Redis 默认
DEFAULT_REDIS_ADDR: str = "127.0.0.1:6379"
DEFAULT_QUEUE_TYPE: str = "stream"
DEFAULT_INGEST_KEY: str = "trace:ingest"
DEFAULT_CACHE_PREFIX: str = "trace:"
DEFAULT_CACHE_TTL_SEC: int = 60
DEFAULT_QUEUE_SOFT_LIMIT: int = 100_000
DEFAULT_MAX_BATCH: int = 500

# SQLite 只读 URI 查询参数
SQLITE_BUSY_TIMEOUT_MS: int = 5000
