# traceService — 轻量 Trace / 日志查询

## 是什么

独立的可观测子系统：接收各业务服务上报的结构化日志，按 **`trace_id`** 检索跨服务日志**时间线**，并提供简单 Web UI。

**不是**完整 APM / Jaeger / ELK。MVP 目标是：本地与联调时，任意请求只要带 `trace_id`，就能在本服务里查到链路日志。

## 为何独立

- 主业务 Go 微服务脚手架未就绪时，也可先开发、联调可观测。
- 不阻塞 gateway / user / drama / ai 的落地节奏。
- 主仓业务服务**不 import** 本目录代码，只通过约定协议（HTTP ingest / 文件）上报。

## 技术栈（MVP）

| 层 | 选型 | 备注 |
|----|------|------|
| 后端 | Python **FastAPI** | 配置 YAML |
| 前端 | **Vue3** | 独立于主仓 `web/` |
| 存储 | **SQLite** | 可复议为 PostgreSQL |
| 上报 | HTTP `POST /api/v1/logs/ingest` | 默认；本地也可文件尾随采集 |

## 功能（规划）

1. 日志 **ingest** API（单条 / 批量）
2. 按 **`trace_id`** 查询，结果按时间升序
3. 简单 Web：输入框 + 时间线列表
4. （可选）模拟日志生成脚本，便于无业务服务时自测

## 目录结构（规划）

```
traceService/
├── README.md
├── .gitignore
├── docs/
│   ├── PLAN.md              # 开发计划（checkbox）
│   └── ARCHITECTURE.md      # 数据流说明
├── backend/                 # FastAPI 应用（待实现）
│   └── .gitkeep
└── frontend/                # Vue3 查询 UI（待实现）
    └── .gitkeep
```

实现阶段预计再细分：`backend/app/main.py`、`backend/app/api/`、`backend/app/models/`、`backend/configs/`、`frontend/src/` 等——以 `docs/PLAN.md` 为准。

## 本地启动（预期命令，实现后可跑）

> 当前以文档与计划为主，代码尚未实现。下列为占位约定。

```bash
# 后端
cd traceService/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100

# 前端（另开终端）
cd traceService/frontend
pnpm install && pnpm dev   # 预期端口如 5174，以实际为准
```

健康检查（预期）：`GET http://127.0.0.1:8100/healthz`

## 与主仓约定

### Header

- 全链路：`X-Trace-Id: <uuid>`
- 业务网关 / 服务同时透传 `x-user-id`（日志里可作为 fields）

### 日志 JSON Schema 示例

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "a1b2c3d4e5f67890",
  "service": "gateway",
  "level": "INFO",
  "message": "request handled",
  "timestamp": "2026-09-27T22:00:00+08:00",
  "fields": {
    "method": "POST",
    "path": "/api/v1/projects",
    "user_id": "u_123"
  }
}
```

必填建议：`trace_id`、`service`、`level`、`message`、`timestamp`。`span_id` / `fields` 可选。

### Ingest（默认）

```http
POST /api/v1/logs/ingest
Content-Type: application/json

{ "logs": [ { ...一条或多条日志对象... } ] }
```

单条也可接受同一 schema 的对象 body（实现时二选一或兼容，见 PLAN）。

### 查询

```http
GET /api/v1/logs?trace_id=<uuid>
```

返回该 `trace_id` 下按 `timestamp` 升序的日志列表，供 Web 时间线渲染。

## 相关文档

- 开发计划：[`docs/PLAN.md`](docs/PLAN.md)
- 架构数据流：[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- 仓库宪法：[`../AGENTS.md`](../AGENTS.md) §D / §I
