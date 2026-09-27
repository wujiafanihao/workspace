"""errors.py — 业务错误码与 BizError。

负责：集中错误码定义、BizError 异常、HTTP 状态映射。
不负责：框架级 HTTPException 细节（由 API 层捕获后包装）。
依赖：无。
"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    """业务错误码常量（禁止在业务文件散落魔法数字）。"""

    OK: int = 0
    BAD_REQUEST: int = 40001
    INTERNAL: int = 50000
    QUEUE_UNAVAILABLE: int = 50301


# code -> 默认 HTTP status
HTTP_STATUS_BY_CODE: dict[int, int] = {
    ErrorCode.OK: 200,
    ErrorCode.BAD_REQUEST: 400,
    ErrorCode.INTERNAL: 500,
    ErrorCode.QUEUE_UNAVAILABLE: 503,
}

# code -> 默认 message
MESSAGE_BY_CODE: dict[int, str] = {
    ErrorCode.OK: "ok",
    ErrorCode.BAD_REQUEST: "validation failed",
    ErrorCode.INTERNAL: "internal error",
    ErrorCode.QUEUE_UNAVAILABLE: "queue unavailable or over soft limit",
}


class BizError(Exception):
    """业务异常：携带统一错误码与可选 data。

    入参：code 业务码；message 可读说明；data 可选载荷。
    副作用：无；由全局 handler 转为 {code,message,data} 响应。
    """

    def __init__(
        self,
        code: int,
        message: str | None = None,
        data: Any = None,
    ) -> None:
        self.code = code
        self.message = message or MESSAGE_BY_CODE.get(code, "error")
        self.data = data
        super().__init__(self.message)

    @property
    def http_status(self) -> int:
        """映射到 HTTP 状态码。"""
        return HTTP_STATUS_BY_CODE.get(self.code, 500)
