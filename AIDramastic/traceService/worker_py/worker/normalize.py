"""normalize.py — 日志条目校验与规范化。

负责：level 大写、msg→message、补全 fields；过滤非法条。
不负责：入队、写库。
依赖：无。
"""

from __future__ import annotations

from typing import Any, Optional


REQUIRED = ("trace_id", "service", "level", "timestamp")


def normalize_item(raw: dict[str, Any]) -> Optional[dict[str, Any]]:
    """规范化单条日志。

    入参：原始 dict（可含 msg）。出参：规范化 dict，非法返回 None。
    副作用：无。
    """
    if not isinstance(raw, dict):
        return None
    message = raw.get("message")
    if message is None:
        message = raw.get("msg")
    if message is None or str(message).strip() == "":
        return None
    for key in REQUIRED:
        val = raw.get(key)
        if val is None or str(val).strip() == "":
            return None
    level = str(raw.get("level", "")).upper()
    fields = raw.get("fields")
    if fields is None:
        fields = {}
    if not isinstance(fields, dict):
        return None
    return {
        "trace_id": str(raw["trace_id"]),
        "span_id": raw.get("span_id"),
        "service": str(raw["service"]),
        "level": level,
        "message": str(message),
        "timestamp": str(raw["timestamp"]),
        "fields": fields,
    }


def normalize_batch(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """批量规范化，跳过非法条目。"""
    out: list[dict[str, Any]] = []
    for item in items:
        n = normalize_item(item)
        if n is not None:
            out.append(n)
    return out
