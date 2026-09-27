#!/usr/bin/env python3
"""gen_mock_logs.py — 向 ingest API 推送多服务交错日志（联调用）。

负责：生成同一 trace_id 的 gateway/user-svc/ai-svc 日志并 POST。
不负责：起 Worker / 查库。
依赖：httpx（或 urllib）。
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib import error, request

CST = timezone(timedelta(hours=8))


def main() -> int:
    """CLI 入口；打印 trace_id；返回进程码。"""
    p = argparse.ArgumentParser(description="mock multi-service logs ingest")
    p.add_argument("--base", default="http://127.0.0.1:8100")
    p.add_argument("--trace-id", default="")
    args = p.parse_args()
    tid = args.trace_id or str(uuid.uuid4())
    base_ts = datetime.now(CST)
    services = [
        ("gateway", "INFO", "request start"),
        ("user-svc", "INFO", "auth ok"),
        ("ai-svc", "INFO", "job running"),
        ("ai-svc", "ERROR", "mock fail example"),
    ]
    logs = []
    for i, (svc, level, msg) in enumerate(services):
        ts = (base_ts + timedelta(milliseconds=10 * i)).isoformat()
        logs.append(
            {
                "trace_id": tid,
                "span_id": f"span-{i}",
                "service": svc,
                "level": level,
                "message": msg,
                "timestamp": ts,
                "fields": {"i": i},
            }
        )
    body = json.dumps({"logs": logs}).encode("utf-8")
    req = request.Request(
        f"{args.base.rstrip('/')}/api/v1/logs/ingest",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=2.0) as resp:
            raw = resp.read().decode("utf-8")
            print(raw)
            print(f"trace_id={tid}", file=sys.stderr)
            return 0
    except error.URLError as exc:
        print(f"ingest failed: {exc}", file=sys.stderr)
        print(f"trace_id={tid}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
