"""constants.py — Python Worker 常量。"""

from __future__ import annotations

SERVICE_NAME: str = "trace-worker-py"
DEFAULT_REDIS_ADDR: str = "127.0.0.1:6379"
DEFAULT_STREAM_MAXLEN: int = 100_000  # persist XADD ~ MAXLEN
