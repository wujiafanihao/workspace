"""config_test.py — load_config / RedisConfig 默认值。"""

from __future__ import annotations

from pathlib import Path

from app.config import RedisConfig, load_config
from app.constants import DEFAULT_QUEUE_SOFT_LIMIT, DEFAULT_STREAM_MAXLEN


def test_redis_config_stream_maxlen_default():
    cfg = RedisConfig()
    assert cfg.stream_maxlen == DEFAULT_STREAM_MAXLEN
    assert cfg.stream_maxlen == DEFAULT_QUEUE_SOFT_LIMIT


def test_load_config_stream_maxlen_defaults_to_soft_limit(tmp_path: Path):
    yaml_path = tmp_path / "default.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                "redis:",
                '  ingest_queue_key: "trace:ingest"',
                '  queue_type: "stream"',
                "  queue_soft_limit: 12345",
                "sqlite:",
                '  path: "./data/logs.db"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_config(yaml_path)
    assert cfg.redis.queue_soft_limit == 12345
    assert cfg.redis.stream_maxlen == 12345


def test_load_config_stream_maxlen_explicit(tmp_path: Path):
    yaml_path = tmp_path / "default.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                "redis:",
                "  queue_soft_limit: 100000",
                "  stream_maxlen: 777",
                "sqlite:",
                '  path: "./data/logs.db"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    cfg = load_config(yaml_path)
    assert cfg.redis.stream_maxlen == 777
