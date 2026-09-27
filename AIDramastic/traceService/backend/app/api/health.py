"""health.py — 健康检查路由。

负责：GET /healthz → {status: ok}。
不负责：深度依赖探测（可复议 queue_depth）。
依赖：fastapi。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/healthz")
async def healthz() -> dict[str, str]:
    """健康探针；返回 {status: ok}。无副作用。"""
    return {"status": "ok"}
