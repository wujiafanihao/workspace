"""main.py — FastAPI 应用入口。

负责：CORS、lifespan（redis 池 + schema ensure）、挂载路由、统一错误包络。
不负责：Worker 消费；SQLite 业务写入。
依赖：config、redis_client、db、api.*、errors。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.api import health, ingest, query
from app.config import load_config
from app.constants import CODE_OK, MSG_OK
from app.db import ensure_schema
from app.errors import BizError, ErrorCode
from app.logger import get_logger
from app.redis_client import close_redis, init_redis

log = get_logger(__name__)


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
    app = FastAPI(title="traceService", version="0.1.0", lifespan=lifespan)
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
                "data": {"errors": exc.errors()},
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
