"""health.py — 健康检查路由。

负责：GET /healthz → {status: ok}。
不负责：深度依赖探测（可复议 queue_depth）。
依赖：fastapi。
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    summary="健康检查",
    description=(
        "进程存活探针。返回 `{status: ok}`。"
        "不探测 Redis / SQLite 是否可用；用于负载均衡或本地冒烟。"
    ),
    responses={
        200: {
            "description": "服务进程正常",
            "content": {
                "application/json": {
                    "example": {"status": "ok"},
                }
            },
        }
    },
)
async def healthz() -> dict[str, str]:
    """健康探针；返回 {status: ok}。无副作用。"""
    return {"status": "ok"}
