"""main.py — Python Worker 进程入口。

负责：加载配置、注册 SIGINT/SIGTERM、启动 Consumer。
不负责：写 SQLite。
依赖：config、consumer。
"""

from __future__ import annotations

import asyncio
import signal
from typing import Any

from worker.config import load_config
from worker.consumer import Consumer
from worker.log import get_logger

log = get_logger(__name__)


def main() -> int:
    """启动 worker；优雅退出返回 0。"""
    cfg = load_config()
    consumer = Consumer(cfg)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def _handle_sig(*_args: Any) -> None:
        log.info("signal received, shutting down")
        consumer.request_stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_sig)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _handle_sig())

    try:
        loop.run_until_complete(consumer.run())
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
