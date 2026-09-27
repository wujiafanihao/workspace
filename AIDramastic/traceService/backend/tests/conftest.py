"""conftest — API 集成测试用 fakeredis 覆盖 redis 池。"""

from __future__ import annotations

import pytest
import fakeredis.aioredis
from httpx import ASGITransport, AsyncClient

from app import redis_client
from app.db import ensure_schema
from app.main import create_app
import app.config as config_mod
import app.main as main_mod


@pytest.fixture
async def api_client(tmp_path, monkeypatch):
    """提供挂载 fakeredis 与临时 sqlite 的 AsyncClient。

    不依赖 ASGI lifespan（部分 httpx 版本无 lifespan 参数）；
    直接注入 _pool 与 app.state.cfg。
    """
    db_path = str(tmp_path / "logs.db")
    yaml_path = tmp_path / "default.yaml"
    yaml_path.write_text(
        "\n".join(
            [
                "server:",
                '  host: "127.0.0.1"',
                "  port: 8100",
                "redis:",
                "  addr_env: REDIS_ADDR",
                "  password_env: REDIS_PASSWORD",
                '  ingest_queue_key: "trace:ingest"',
                '  persist_queue_key: "trace:persist"',
                '  queue_type: "stream"',
                '  cache_prefix: "trace:"',
                "  cache_ttl_sec: 60",
                "  queue_soft_limit: 100000",
                "sqlite:",
                f'  path: "{db_path}"',
                "cors:",
                "  origins:",
                '    - "http://127.0.0.1:5174"',
                "ingest:",
                "  max_batch: 500",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("REDIS_ADDR", "127.0.0.1:6379")

    real_load = config_mod.load_config

    def _load(_path=None):
        return real_load(yaml_path)

    monkeypatch.setattr(config_mod, "load_config", _load)
    monkeypatch.setattr(main_mod, "load_config", _load)

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    await ensure_schema(db_path)
    redis_client._pool = fake

    app = create_app()
    app.state.cfg = _load()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        redis_client._pool = fake
        yield client, fake, db_path

    redis_client._pool = None
    await fake.aclose()
