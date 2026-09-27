"""log.py — Worker 结构化 JSON 日志。"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from worker.constants import SERVICE_NAME

_CST = timezone(timedelta(hours=8))


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(_CST).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        tid = getattr(record, "trace_id", None)
        if tid:
            payload["trace_id"] = tid
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = SERVICE_NAME) -> logging.Logger:
    """获取 JSON logger。"""
    logger = logging.getLogger(name)
    if not logger.handlers:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(_JsonFormatter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
