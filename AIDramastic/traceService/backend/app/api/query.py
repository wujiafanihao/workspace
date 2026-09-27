"""query.py — 按 trace_id 查询日志 API。

负责：GET /api/v1/logs?trace_id= → cache → SQLite ORDER BY timestamp ASC。
不负责：写入；缓存失效。
依赖：services.cache；db.fetch_logs_by_trace_id。
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query, Request

from app.constants import CODE_OK, MSG_OK
from app.db import fetch_logs_by_trace_id
from app.errors import BizError, ErrorCode
from app.logger import get_logger
from app.redis_client import get_redis
from app.schemas.log import Envelope, QueryData
from app.services import cache as cache_svc

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/logs", tags=["query"])


@router.get(
    "",
    response_model=Envelope,
    summary="按 trace_id 查询日志时间线",
    description=(
        "根据 `trace_id` 返回跨服务日志时间线（按 `timestamp` 升序）。"
        "\n\n"
        "查询顺序：Redis 缓存 → miss 时只读 SQLite 并回填缓存。"
        "\n\n"
        "- `trace_id` 必填；缺参或空白 → 业务码 40001。\n"
        "- 无数据时 `data.logs` 为空数组（仍返回成功码 0）。"
    ),
    responses={
        200: {
            "description": "查询成功（可能 logs 为空）",
            "content": {
                "application/json": {
                    "example": {
                        "code": 0,
                        "message": "ok",
                        "data": {
                            "trace_id": "11111111-1111-1111-1111-111111111111",
                            "logs": [
                                {
                                    "id": 1,
                                    "trace_id": "11111111-1111-1111-1111-111111111111",
                                    "span_id": "span-0",
                                    "service": "gateway",
                                    "level": "INFO",
                                    "message": "request start",
                                    "timestamp": "2026-09-27T22:00:00+08:00",
                                    "fields": {},
                                }
                            ],
                        },
                    }
                }
            },
        },
        400: {
            "description": "缺少 trace_id",
            "content": {
                "application/json": {
                    "example": {
                        "code": 40001,
                        "message": "trace_id is required",
                        "data": None,
                    }
                }
            },
        },
    },
)
async def query_logs(
    request: Request,
    trace_id: Optional[str] = Query(
        default=None,
        description="必填。全链路追踪 ID；用于拉取该链路下全部日志。",
        examples=["11111111-1111-1111-1111-111111111111"],
    ),
) -> Envelope:
    """按 trace_id 查询时间线。

    入参：trace_id 必填；缺参 → 40001。
    出参：Envelope(data={trace_id, logs})；无数据 logs=[]。
    副作用：cache GET；miss 时只读 SELECT + SETEX 回填。
    """
    if trace_id is None or str(trace_id).strip() == "":
        raise BizError(ErrorCode.BAD_REQUEST, message="trace_id is required")

    tid = str(trace_id).strip()
    cfg = request.app.state.cfg
    client = get_redis()

    cached = await cache_svc.get_trace_logs(client, cfg.redis, tid)
    if cached is not None:
        log.info("query cache hit", extra={"trace_id": tid})
        return Envelope(
            code=CODE_OK,
            message=MSG_OK,
            data=QueryData(trace_id=tid, logs=cached).model_dump(),  # type: ignore[arg-type]
        )

    rows = await fetch_logs_by_trace_id(cfg.sqlite.path, tid)
    await cache_svc.set_trace_logs(client, cfg.redis, tid, rows)
    log.info(
        "query cache miss",
        extra={"trace_id": tid, "fields": {"count": len(rows)}},
    )
    return Envelope(
        code=CODE_OK,
        message=MSG_OK,
        data=QueryData(trace_id=tid, logs=rows).model_dump(),  # type: ignore[arg-type]
    )
