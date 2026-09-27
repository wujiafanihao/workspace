"""logger.py — 统一结构化 JSON 日志封装。

负责：按 AGENTS 要求输出 JSON 一行一条（时间/level/service/trace_id/msg）。
不负责：业务日志内容决策；禁止业务侧 print。
依赖：constants.SERVICE_NAME；标准 logging。
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import Any

from app.constants import SERVICE_NAME

_CST = timezone(timedelta(hours=8))


class _JsonFormatter(logging.Formatter):
    """将 LogRecord 格式化为单行 JSON。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(_CST).isoformat(),
            "level": record.levelname,
            "service": SERVICE_NAME,
            "message": record.getMessage(),
        }
        trace_id = getattr(record, "trace_id", None)
        if trace_id:
            payload["trace_id"] = trace_id
        if record.exc_info:
            payload["err"] = self.formatException(record.exc_info)
        extra_fields = getattr(record, "fields", None)
        if isinstance(extra_fields, dict):
            payload["fields"] = extra_fields
        return json.dumps(payload, ensure_ascii=False)


def get_logger(name: str = SERVICE_NAME) -> logging.Logger:
    """获取或创建带 JSON formatter 的 logger。

    入参：name 模块名。出参：logging.Logger。
    副作用：首次调用时配置 StreamHandler 到 stderr。
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger
