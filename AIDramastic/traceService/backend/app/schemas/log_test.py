"""log_test.py — LogIn message/msg 别名与校验。"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.log import IngestBody, LogIn


def test_message_direct():
    m = LogIn(
        trace_id="t",
        service="gateway",
        level="info",
        message="hello",
        timestamp="2026-09-27T22:00:00+08:00",
    )
    assert m.message == "hello"
    d = m.to_queue_dict()
    assert d["message"] == "hello"
    assert "msg" not in d


def test_msg_alias():
    m = LogIn(
        trace_id="t",
        service="gateway",
        level="INFO",
        msg="via-msg",
        timestamp="2026-09-27T22:00:00+08:00",
    )
    assert m.message == "via-msg"


def test_missing_message_fails():
    with pytest.raises(ValidationError):
        LogIn(
            trace_id="t",
            service="gateway",
            level="INFO",
            timestamp="2026-09-27T22:00:00+08:00",
        )


def test_fields_must_be_object():
    with pytest.raises(ValidationError):
        LogIn(
            trace_id="t",
            service="gateway",
            level="INFO",
            message="m",
            timestamp="t",
            fields="bad",  # type: ignore[arg-type]
        )


def test_ingest_body_min_one():
    with pytest.raises(ValidationError):
        IngestBody(logs=[])
