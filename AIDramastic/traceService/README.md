# traceService — 轻量 Trace / 日志查询

## 是什么

独立可观测子系统：接收各业务服务上报的结构化日志，经 **两级 Redis 队列**，由 **Python Worker** 规范化后再由 **Go Worker** 批量写入 **SQLite**，并按 **`trace_id`** 提供查询与简单 Web 时间线。

**不是**完整 APM / Jaeger / ELK。

## 背景（加长）

AIDramastic 主业务是多进程 Go 服务（gateway / user / drama / ai），业务数据在 **MySQL**，Redis 做队列/缓存/JWT 黑名单。联调时需要「一个 `trace_id` 拉齐全链路日志」，但：

- 不能把日志主存储塞进业务 MySQL 抢锁；
- 不能强迫先上 Jaeger 集群；
- **绝不能**让日志上报拖慢用户请求。

因此本目录提供本地可起的轻量方案：上报异步、ingest 只入队、规范化与落库分属 **Python Worker / Go Worker**。

## 定死架构（两级队列 + 双 Worker）

```
业务服务 (async, timeout 短, 失败可丢)
    → POST /api/v1/logs/ingest
    → FastAPI 轻量校验 → Redis `trace:ingest` → 立即返回
    → Python Worker：校验/规范化/enrich → Redis `trace:persist`
    → Go Worker：批量写 SQLite (WAL) + 更新查询缓存
    → GET 查询：Redis 缓存 → SQLite → 回填
    → Vue3 Web 时间线
```

| 层 | 选型 | 备注 |
|----|------|------|
| API | Python **FastAPI** | ingest 入队 + query + health |
| Python Worker | **Python**（必须） | `traceService/worker_py`；消费 `trace:ingest` |
| Go Worker | **Go**（必须） | `traceService/worker`；消费 `trace:persist`；**唯一** SQLite 写者 |
| 前端 | **Vue3** | 独立于主仓 `web/` |
| 持久化 | **SQLite** | 写死；MVP 不改 MySQL |
| 缓冲/缓存 | **Redis** | 写死；两级队列 + 查询缓存 |

技术栈一句话：**FastAPI API + Python Worker + Go Worker + Vue3 + Redis + SQLite**。

**可复议**：合并某级 Worker；MVP 保持双 Worker 两级队列。

**存储边界**：主业务 **MySQL**；本服务 **SQLite**。见根目录 `AGENTS.md` §J / **§K**。

## 功能（规划）

1. 日志 ingest（单条/批量）→ `trace:ingest`
2. Python Worker 规范化 → `trace:persist`
3. Go Worker 消费落库 + 缓存维护
4. 按 `trace_id` 查询（时间升序）
5. Web：输入框 + 时间线
6. （可选）mock 脚本、限流、retention

## 目录结构

```
traceService/
├── README.md
├── .gitignore
├── docs/
│   ├── README.md
│   ├── PRD.md
│   ├── DESIGN.md
│   ├── ARCHITECTURE.md
│   ├── PLAN.md
│   └── TODO.md
├── backend/                 # FastAPI API（待实现）
│   └── .gitkeep
├── worker_py/               # Python Worker（待实现）
│   └── .gitkeep
├── worker/                  # Go Worker（待实现）
│   └── .gitkeep
└── frontend/                # Vue3（待实现）
    └── .gitkeep
```

## 文档地图

| 文档 | 说明 |
|------|------|
| [`docs/PRD.md`](docs/PRD.md) | 需求与验收 |
| [`docs/DESIGN.md`](docs/DESIGN.md) | 详细设计 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 架构与序列图 |
| [`docs/PLAN.md`](docs/PLAN.md) | 开发计划（含 Python Worker / Go Worker Task） |
| [`docs/TODO.md`](docs/TODO.md) | 执行细清单 |
| [`../AGENTS.md`](../AGENTS.md) | 工程宪法 §D/§I/§J/**§K** |

## 本地启动（预期命令，实现后可跑）

> 当前以文档与计划为主。下列为占位约定。

```bash
# 0. Redis
redis-server   # 或 docker run redis

# 1. API
cd traceService/backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8100

# 2. Python Worker（另开终端）
cd traceService/worker_py
python -m worker   # 或按 PLAN 落地后的入口

# 3. Go Worker（另开终端）
cd traceService/worker
go run ./cmd/worker

# 4. 前端（另开终端）
cd traceService/frontend
pnpm install && pnpm dev   # 预期 :5174
```

健康检查：`GET http://127.0.0.1:8100/healthz`

## 与主仓约定

### Header

- `X-Trace-Id: <uuid>`
- 可选透传 `x-user-id`（进 fields）

### 日志 JSON

```json
{
  "trace_id": "550e8400-e29b-41d4-a716-446655440000",
  "span_id": "a1b2c3d4e5f67890",
  "service": "gateway",
  "level": "INFO",
  "message": "request handled",
  "timestamp": "2026-09-27T22:00:00+08:00",
  "fields": { "method": "POST", "path": "/api/v1/projects", "user_id": "u_123" }
}
```

必填：`trace_id`、`service`、`level`、`message`、`timestamp`。

### Ingest / Query

```http
POST /api/v1/logs/ingest
Content-Type: application/json

{ "logs": [ { ... } ] }
```

```http
GET /api/v1/logs?trace_id=<uuid>
```

业务侧必须 **异步调用** ingest（短超时、失败可丢），详见主仓 `DESIGN.md` 与 `AGENTS.md` §K。
