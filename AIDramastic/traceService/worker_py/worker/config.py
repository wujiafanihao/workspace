"""config.py — worker_py YAML 配置。

负责：加载 configs/default.yaml；解析 Redis 地址 env。
不负责：热更。
依赖：pyyaml。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from worker.constants import DEFAULT_REDIS_ADDR


@dataclass
class RedisCfg:
    addr: str = DEFAULT_REDIS_ADDR
    password: str | None = None
    ingest_queue_key: str = "trace:ingest"
    persist_queue_key: str = "trace:persist"
    queue_type: str = "stream"
    group: str = "trace-ingest-workers"
    consumer: str = "py-worker-1"
    claim_min_idle_ms: int = 60000  # PEL 最小空闲毫秒，XAUTOCLAIM min_idle_time
    claim_count: int = 0  # 每次 claim 条数；<=0 则用 max_batch


@dataclass
class NormalizeCfg:
    max_batch: int = 100
    flush_interval_ms: int = 50


@dataclass
class WorkerConfig:
    redis: RedisCfg = field(default_factory=RedisCfg)
    normalize: NormalizeCfg = field(default_factory=NormalizeCfg)


def load_config(path: str | Path | None = None) -> WorkerConfig:
    """加载 YAML 配置。"""
    root = Path(__file__).resolve().parent.parent
    cfg_path = Path(path) if path else root / "configs" / "default.yaml"
    raw: dict[str, Any] = {}
    if cfg_path.is_file():
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    r = raw.get("redis") or {}
    n = raw.get("normalize") or {}
    addr_env = r.get("addr_env", "REDIS_ADDR")
    password_env = r.get("password_env", "REDIS_PASSWORD")
    claim_min_idle_ms = int(r.get("claim_min_idle_ms", 60000) or 60000)
    if claim_min_idle_ms <= 0:
        claim_min_idle_ms = 60000
    # claim_count <= 0：运行时回退到 normalize.max_batch
    claim_count = int(r.get("claim_count", 0) or 0)
    return WorkerConfig(
        redis=RedisCfg(
            addr=os.environ.get(addr_env) or DEFAULT_REDIS_ADDR,
            password=os.environ.get(password_env) or None,
            ingest_queue_key=str(r.get("ingest_queue_key", "trace:ingest")),
            persist_queue_key=str(r.get("persist_queue_key", "trace:persist")),
            queue_type=str(r.get("queue_type", "stream")),
            group=str(r.get("group", "trace-ingest-workers")),
            consumer=str(r.get("consumer", "py-worker-1")),
            claim_min_idle_ms=claim_min_idle_ms,
            claim_count=claim_count,
        ),
        normalize=NormalizeCfg(
            max_batch=int(n.get("max_batch", 100)),
            flush_interval_ms=int(n.get("flush_interval_ms", 50)),
        ),
    )
