"""main.py — FastAPI 应用入口。

负责：CORS、lifespan（redis 池 + schema ensure）、挂载路由、统一错误包络、中文 OpenAPI。
不负责：Worker 消费；SQLite 业务写入。
依赖：config、redis_client、db、api.*、errors。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import health, ingest, query
from app.config import load_config
from app.db import ensure_schema
from app.errors import BizError, ErrorCode
from app.logger import get_logger
from app.redis_client import close_redis, init_redis

log = get_logger(__name__)

OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "健康检查：进程存活探针，不探测 Redis/SQLite 深度依赖。",
    },
    {
        "name": "ingest",
        "description": "日志采集：批量校验后仅写入 Redis 队列 `trace:ingest`，不写 SQLite。",
    },
    {
        "name": "query",
        "description": "日志查询：按 `trace_id` 查时间线，优先 Redis 缓存，未命中再读 SQLite。",
    },
]

APP_DESCRIPTION = """
## 简介

traceService FastAPI：跨服务链路日志的 **采集入队** 与 **按 trace_id 查询**。

## 架构要点

- **ingest**：轻量校验 → Redis `trace:ingest` → 立即返回（SQLite 由 Go Worker 写入）
- **query**：Redis 缓存 → SQLite `ORDER BY timestamp ASC`
- **healthz**：存活探针

## 统一响应

业务接口成功/失败均为 `{ "code", "message", "data" }` 包络（healthz 除外）。

## 文档入口

- Swagger UI：`/docs`
- ReDoc：`/redoc`
- OpenAPI JSON：`/openapi.json`（亦导出至 `data/openapi.json` 供 Apifox 导入）
""".strip()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动建池/ensure schema；关闭关池。"""
    cfg = load_config()
    app.state.cfg = cfg
    await init_redis(cfg.redis)
    # 只读侧建表便于本地 query；生产写由 Go Worker 负责
    await ensure_schema(cfg.sqlite.path)
    log.info(
        "api started",
        extra={
            "fields": {
                "host": cfg.server.host,
                "port": cfg.server.port,
                "sqlite": cfg.sqlite.path,
            }
        },
    )
    yield
    await close_redis()
    log.info("api stopped")


def create_app() -> FastAPI:
    """工厂：创建已挂载路由与中间件的 FastAPI 实例。"""
    cfg = load_config()
    app = FastAPI(
        title="traceService 链路日志服务",
        description=APP_DESCRIPTION,
        version="0.1.0",
        openapi_tags=OPENAPI_TAGS,
        lifespan=lifespan,
    )
    app.state.cfg = cfg

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors.origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(BizError)
    async def _biz_error_handler(_request: Request, exc: BizError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.http_status,
            content={"code": exc.code, "message": exc.message, "data": exc.data},
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={
                "code": ErrorCode.BAD_REQUEST,
                "message": "validation failed",
                "data": {
                    "errors": jsonable_encoder(
                        exc.errors(), custom_encoder={Exception: str}
                    )
                },
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        log.error("unhandled error", extra={"fields": {"err": str(exc)}})
        return JSONResponse(
            status_code=500,
            content={
                "code": ErrorCode.INTERNAL,
                "message": "internal error",
                "data": None,
            },
        )

    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(query.router)
    return app


app = create_app()
