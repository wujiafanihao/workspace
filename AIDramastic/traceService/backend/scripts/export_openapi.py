#!/usr/bin/env python3
"""export_openapi.py — 导出 FastAPI OpenAPI 3 JSON 供 Apifox 导入。

负责：import create_app → app.openapi() → 写入 backend/data/openapi.json。
不负责：启动服务 / 连接 Redis（不触发 lifespan）。
依赖：app.main.create_app。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    """生成 OpenAPI JSON；成功返回 0。"""
    backend_root = Path(__file__).resolve().parents[1]
    # 保证可 `python scripts/export_openapi.py` 从任意 cwd
    if str(backend_root) not in sys.path:
        sys.path.insert(0, str(backend_root))

    from app.main import create_app

    app = create_app()
    schema = app.openapi()
    out = backend_root / "data" / "openapi.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {out} ({out.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
