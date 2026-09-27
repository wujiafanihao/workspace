# plan — Swagger 中文 OpenAPI

| 字段 | 内容 |
|------|------|
| 日期 | 2026-09-27 |
| 状态 | archive |

## 背景

traceService FastAPI 需提供 `/docs` 中文 API 文档，并导出 OpenAPI JSON 供 Apifox 导入。

## 一句话目标

启用中文 Swagger/OpenAPI，导出并提交 `backend/data/openapi.json`。

## 范围

- FastAPI 中文 title/description/tags/路由 summary
- schemas 中文 Field 描述
- `scripts/export_openapi.py` + 提交 openapi.json
- 聚焦 openapi 单测；`.gitignore` 白名单

## 非范围

- 改业务逻辑；起 Redis；改前端

## 验收标准

1. `/docs`、`/openapi.json`、`/redoc` 可用（默认开启）
2. `openapi.json` 含中文 title 与 healthz/ingest/query paths
3. `conda run -n workspace pytest -q` 通过
4. 一次 commit 并 push
