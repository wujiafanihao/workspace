"""log.py — 日志 ingest/query 的 Pydantic 模型。

负责：入参校验（LogIn 接受 message 或 msg 别名）、响应包络模型；中文 schema 描述供 OpenAPI/Apifox。
不负责：业务副作用；队列/DB 调用。
依赖：pydantic v2。
"""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LogIn(BaseModel):
    """单条 ingest 入参。

    必填：trace_id / service / level / message|msg / timestamp。
    message 与 msg 互为别名；优先 message。
    """

    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={
            "examples": [
                {
                    "trace_id": "11111111-1111-1111-1111-111111111111",
                    "span_id": "span-0",
                    "service": "gateway",
                    "level": "INFO",
                    "message": "request start",
                    "timestamp": "2026-09-27T22:00:00+08:00",
                    "fields": {"method": "GET", "path": "/api/v1/health"},
                }
            ]
        },
    )

    trace_id: str = Field(
        ...,
        min_length=1,
        description="全链路追踪 ID（UUID 字符串）；跨服务日志关联主键。",
    )
    span_id: Optional[str] = Field(
        default=None,
        description="可选跨度 ID；同一 trace 内区分调用段。",
    )
    service: str = Field(
        ...,
        min_length=1,
        description="服务名，如 gateway / user-svc / ai-svc / trace-api。",
    )
    level: str = Field(
        ...,
        min_length=1,
        description="日志级别：DEBUG / INFO / WARN / ERROR 等。",
    )
    message: Optional[str] = Field(
        default=None,
        description="日志正文；与 msg 二选一，优先 message。",
    )
    msg: Optional[str] = Field(
        default=None,
        description="日志正文别名（兼容旧字段）；与 message 二选一。",
    )
    timestamp: str = Field(
        ...,
        min_length=1,
        description="事件时间，推荐 ISO8601 带时区，如 2026-09-27T22:00:00+08:00。",
    )
    fields: Optional[dict[str, Any]] = Field(
        default=None,
        description="可选扩展字段对象（JSON object）；禁止放入密钥明文。",
    )

    @field_validator("trace_id", "service", "level", "timestamp", mode="before")
    @classmethod
    def _strip_required_text(cls, v: Any) -> Any:
        """Strip required text fields and reject values blank after stripping."""
        if isinstance(v, str):
            value = v.strip()
            if not value:
                raise ValueError("must not be blank")
            return value
        return v

    @model_validator(mode="after")
    def _resolve_message(self) -> "LogIn":
        """将 msg 映射到 message；二者皆空则失败。"""
        text = self.message if self.message is not None else self.msg
        if text is None or str(text).strip() == "":
            raise ValueError("message or msg is required")
        self.message = str(text).strip()
        return self

    @field_validator("fields")
    @classmethod
    def _fields_must_be_object(cls, v: Any) -> Any:
        """fields 若提供必须是 object。"""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("fields must be an object")
        return v

    def to_queue_dict(self) -> dict[str, Any]:
        """转为入队 JSON 友好字典（规范化 message，去掉 msg）。"""
        return {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "service": self.service,
            "level": self.level,
            "message": self.message,
            "timestamp": self.timestamp,
            "fields": self.fields or {},
        }


class IngestBody(BaseModel):
    """批量 ingest 请求体。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "logs": [
                        {
                            "trace_id": "11111111-1111-1111-1111-111111111111",
                            "service": "gateway",
                            "level": "INFO",
                            "message": "request start",
                            "timestamp": "2026-09-27T22:00:00+08:00",
                        }
                    ]
                }
            ]
        }
    )

    logs: list[LogIn] = Field(
        ...,
        min_length=1,
        description="待入队日志列表；至少 1 条，上限见配置 ingest.max_batch。",
    )


class IngestData(BaseModel):
    """ingest 成功 data。"""

    accepted: int = Field(..., description="实际已接受并入队的条数。")


class LogOut(BaseModel):
    """单条查询出参。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "trace_id": "11111111-1111-1111-1111-111111111111",
                    "span_id": "span-0",
                    "service": "gateway",
                    "level": "INFO",
                    "message": "request start",
                    "timestamp": "2026-09-27T22:00:00+08:00",
                    "fields": {"method": "GET"},
                }
            ]
        }
    )

    id: Optional[int] = Field(default=None, description="SQLite 行 ID；缓存命中时可能为空。")
    trace_id: str = Field(..., description="全链路追踪 ID。")
    span_id: Optional[str] = Field(default=None, description="可选跨度 ID。")
    service: str = Field(..., description="服务名。")
    level: str = Field(..., description="日志级别。")
    message: str = Field(..., description="日志正文。")
    timestamp: str = Field(..., description="事件时间（ISO8601 或入库原样）。")
    fields: dict[str, Any] = Field(
        default_factory=dict,
        description="扩展字段对象。",
    )


class QueryData(BaseModel):
    """query 成功 data。"""

    trace_id: str = Field(..., description="查询的 trace_id。")
    logs: list[LogOut] = Field(
        ...,
        description="按 timestamp 升序的日志时间线；无数据时为空数组。",
    )


class Envelope(BaseModel):
    """统一响应包络 {code,message,data}。"""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "code": 0,
                    "message": "ok",
                    "data": {"accepted": 1},
                }
            ]
        }
    )

    code: int = Field(..., description="业务码；0 表示成功，非 0 为错误（如 40001）。")
    message: str = Field(..., description="人类可读说明。")
    data: Any = Field(default=None, description="业务数据；失败时可为错误细节或 null。")
