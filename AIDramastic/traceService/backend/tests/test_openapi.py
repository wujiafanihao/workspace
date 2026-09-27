"""test_openapi.py — 校验中文 OpenAPI 元数据与关键 paths（无需 Redis）。"""

from __future__ import annotations

from app.main import create_app


def test_openapi_chinese_metadata_and_paths():
    """app.openapi() 含中文 title/description，且含 healthz/ingest/query。"""
    app = create_app()
    schema = app.openapi()

    assert "链路日志" in schema["info"]["title"]
    assert "traceService" in schema["info"]["title"]
    desc = schema["info"].get("description") or ""
    assert "ingest" in desc.lower() or "采集" in desc
    assert "查询" in desc or "query" in desc.lower()

    paths = schema["paths"]
    assert "/healthz" in paths
    assert "/api/v1/logs/ingest" in paths
    assert "/api/v1/logs" in paths

    tags = {t["name"]: t.get("description", "") for t in schema.get("tags", [])}
    assert "health" in tags and "健康" in tags["health"]
    assert "ingest" in tags and ("采集" in tags["ingest"] or "入队" in tags["ingest"])
    assert "query" in tags and "查询" in tags["query"]

    health_get = paths["/healthz"]["get"]
    assert "健康" in health_get.get("summary", "")

    ingest_post = paths["/api/v1/logs/ingest"]["post"]
    assert "入队" in ingest_post.get("summary", "") or "日志" in ingest_post.get(
        "summary", ""
    )

    query_get = paths["/api/v1/logs"]["get"]
    assert "查询" in query_get.get("summary", "") or "trace" in query_get.get(
        "summary", ""
    ).lower()
