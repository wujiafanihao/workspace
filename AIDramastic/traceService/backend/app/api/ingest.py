"""ingest.py — 日志入队 API。

负责：POST /api/v1/logs/ingest 轻量校验 → enqueue trace:ingest → 立即返回。
不负责：SQLite 写入（禁止）；深度规范化（Python Worker）。
依赖：services.queue；schemas.log；errors。
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.constants import CODE_OK, MSG_OK
from app.errors import BizError, ErrorCode
from app.logger import get_logger
from app.redis_client import get_redis
from app.schemas.log import Envelope, IngestBody, IngestData
from app.services import queue as queue_svc

log = get_logger(__name__)
router = APIRouter(prefix="/api/v1/logs", tags=["ingest"])


@router.post("/ingest", response_model=Envelope)
async def ingest_logs(body: IngestBody, request: Request) -> Envelope:
    """批量 ingest：校验后仅入 Redis，绝不写 SQLite。

    入参：body.logs 至少 1 条。出参：Envelope(data.accepted)。
    副作用：XADD/LPUSH；超批/软上限抛 BizError。
    """
    cfg = request.app.state.cfg
    max_batch = cfg.ingest.max_batch
    if len(body.logs) > max_batch:
        raise BizError(
            ErrorCode.BAD_REQUEST,
            message=f"batch size exceeds max_batch={max_batch}",
        )

    items = [item.to_queue_dict() for item in body.logs]
    client = get_redis()
    accepted = await queue_svc.enqueue_logs(client, cfg.redis, items)
    # 取首条 trace_id 便于可观测（批量可能多 tid）
    tid = items[0].get("trace_id") if items else None
    log.info(
        "ingest accepted",
        extra={"trace_id": tid, "fields": {"accepted": accepted}},
    )
    return Envelope(
        code=CODE_OK,
        message=MSG_OK,
        data=IngestData(accepted=accepted).model_dump(),
    )
