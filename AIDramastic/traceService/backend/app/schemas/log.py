"""log.py — 日志 ingest/query 的 Pydantic 模型。

负责：入参校验（LogIn 接受 message 或 msg 别名）、响应包络模型。
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

    model_config = ConfigDict(extra="ignore")

    trace_id: str = Field(..., min_length=1)
    span_id: Optional[str] = None
    service: str = Field(..., min_length=1)
    level: str = Field(..., min_length=1)
    message: Optional[str] = None
    msg: Optional[str] = None
    timestamp: str = Field(..., min_length=1)
    fields: Optional[dict[str, Any]] = None

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

    logs: list[LogIn] = Field(..., min_length=1)


class IngestData(BaseModel):
    """ingest 成功 data。"""

    accepted: int


class LogOut(BaseModel):
    """单条查询出参。"""

    id: Optional[int] = None
    trace_id: str
    span_id: Optional[str] = None
    service: str
    level: str
    message: str
    timestamp: str
    fields: dict[str, Any] = Field(default_factory=dict)


class QueryData(BaseModel):
    """query 成功 data。"""

    trace_id: str
    logs: list[LogOut]


class Envelope(BaseModel):
    """统一响应包络 {code,message,data}。"""

    code: int
    message: str
    data: Any = None
