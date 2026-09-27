"""config.py — YAML 配置加载。

负责：读取 configs/default.yaml，解析 server/redis/sqlite/cors/ingest。
不负责：热更新 Watch（MVP 不做）；密钥明文（只存 env 名）。
依赖：pyyaml；constants 默认值。
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from app.constants import (
    DEFAULT_CACHE_PREFIX,
    DEFAULT_CACHE_TTL_SEC,
    DEFAULT_INGEST_KEY,
    DEFAULT_MAX_BATCH,
    DEFAULT_QUEUE_SOFT_LIMIT,
    DEFAULT_QUEUE_TYPE,
    DEFAULT_REDIS_ADDR,
)


@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    port: int = 8100


@dataclass
class RedisConfig:
    addr: str = DEFAULT_REDIS_ADDR
    password: str | None = None
    ingest_queue_key: str = DEFAULT_INGEST_KEY
    persist_queue_key: str = "trace:persist"
    queue_type: str = DEFAULT_QUEUE_TYPE
    cache_prefix: str = DEFAULT_CACHE_PREFIX
    cache_ttl_sec: int = DEFAULT_CACHE_TTL_SEC
    queue_soft_limit: int = DEFAULT_QUEUE_SOFT_LIMIT


@dataclass
class SqliteConfig:
    path: str = "./data/logs.db"


@dataclass
class CorsConfig:
    origins: list[str] = field(
        default_factory=lambda: [
            "http://127.0.0.1:5174",
            "http://localhost:5174",
        ]
    )


@dataclass
class IngestConfig:
    max_batch: int = DEFAULT_MAX_BATCH


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    sqlite: SqliteConfig = field(default_factory=SqliteConfig)
    cors: CorsConfig = field(default_factory=CorsConfig)
    ingest: IngestConfig = field(default_factory=IngestConfig)


def _default_config_path() -> Path:
    """解析默认配置路径：backend/configs/default.yaml。"""
    here = Path(__file__).resolve().parent.parent
    return here / "configs" / "default.yaml"


def load_config(path: str | Path | None = None) -> AppConfig:
    """加载 YAML 并合并环境变量解析的 Redis 地址/密码。

    入参：path 可选配置文件路径；None 则用 configs/default.yaml。
    出参：AppConfig 快照。
    副作用：读文件与 os.environ；解析失败抛出异常（启动阶段可 Fatal）。
    """
    cfg_path = Path(path) if path else _default_config_path()
    raw: dict[str, Any] = {}
    if cfg_path.is_file():
        with cfg_path.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    server_raw = raw.get("server") or {}
    redis_raw = raw.get("redis") or {}
    sqlite_raw = raw.get("sqlite") or {}
    cors_raw = raw.get("cors") or {}
    ingest_raw = raw.get("ingest") or {}

    addr_env = redis_raw.get("addr_env", "REDIS_ADDR")
    password_env = redis_raw.get("password_env", "REDIS_PASSWORD")
    addr = os.environ.get(addr_env) or DEFAULT_REDIS_ADDR
    password = os.environ.get(password_env) or None
    if password == "":
        password = None

    # sqlite 相对路径相对 backend 根目录
    sqlite_path = sqlite_raw.get("path", "./data/logs.db")
    if not Path(sqlite_path).is_absolute():
        sqlite_path = str((cfg_path.parent.parent / sqlite_path).resolve())

    return AppConfig(
        server=ServerConfig(
            host=str(server_raw.get("host", "127.0.0.1")),
            port=int(server_raw.get("port", 8100)),
        ),
        redis=RedisConfig(
            addr=addr,
            password=password,
            ingest_queue_key=str(
                redis_raw.get("ingest_queue_key", DEFAULT_INGEST_KEY)
            ),
            persist_queue_key=str(
                redis_raw.get("persist_queue_key", "trace:persist")
            ),
            queue_type=str(redis_raw.get("queue_type", DEFAULT_QUEUE_TYPE)),
            cache_prefix=str(redis_raw.get("cache_prefix", DEFAULT_CACHE_PREFIX)),
            cache_ttl_sec=int(redis_raw.get("cache_ttl_sec", DEFAULT_CACHE_TTL_SEC)),
            queue_soft_limit=int(
                redis_raw.get("queue_soft_limit", DEFAULT_QUEUE_SOFT_LIMIT)
            ),
        ),
        sqlite=SqliteConfig(path=sqlite_path),
        cors=CorsConfig(origins=list(cors_raw.get("origins") or CorsConfig().origins)),
        ingest=IngestConfig(max_batch=int(ingest_raw.get("max_batch", DEFAULT_MAX_BATCH))),
    )
