# traceService 详细设计（DESIGN）

| 字段 | 内容 |
|------|------|
| 文档版本 | v0.3 |
| 日期 | 2026-09-27 |
| 状态 | 现行 |
| 关联 | `PRD.md` / `ARCHITECTURE.md` / `PLAN.md`；`AGENTS.md` §J / §K |

---

## 1. 背景与架构定死

**一句话**：FastAPI 负责 HTTP ingest（入 `trace:ingest`）与 query；**Python Worker** 规范化后入 `trace:persist`；**Go Worker** 批量写 **SQLite**；**Redis** 做两级队列与按 `trace_id` 的查询缓存。

与主仓存储对比：主业务 **MySQL**；本服务 **SQLite only**（持久化）。

```
[Go 业务服务] --async POST--> [FastAPI] --XADD--> [Redis trace:ingest]
                                                      |
                                              [Python Worker]
                                                      | enrich
                                                      v
                                              [Redis trace:persist]
                                                      |
                                              [Go Worker]
                                                      | batch
                                                      v
                                                   [SQLite]
                                                      ^
[Vue3] <--GET-- [FastAPI query: cache -> SQLite -> backfill]
```

---

## 2. 模块划分

### 2.1 backend（Python FastAPI）

| 模块 | 路径（规划） | 职责 |
|------|--------------|------|
| config | `backend/app/config.py` | 加载 YAML：server、redis、sqlite 路径、cors、限流 |
| db | `backend/app/db.py` | **只读** SQLite 连接（query 用）；不在此写日志主路径 |
| schemas | `backend/app/schemas/log.py` | Pydantic 入参/出参 |
| api | `backend/app/api/ingest.py` `query.py` | 路由 |
| services | `backend/app/services/queue.py` `cache.py` | Redis 入队、缓存读写 |
| redis | `backend/app/redis_client.py` | 连接封装 |
| frontend pages | 见 §7 | — |

### 2.2 worker_py（Python Worker，必须）

| 模块 | 路径（规划） | 职责 |
|------|--------------|------|
| main | `worker_py/main.py` 或 `worker_py/worker/__main__.py` | 启动、信号、graceful shutdown |
| config | `worker_py/config.py` | YAML/env；队列 key |
| consumer | `worker_py/consumer.py` | 消费 `trace:ingest`（XREAD/BRPOP） |
| normalize | `worker_py/normalize.py` | 校验/规范化/enrich（level 大小写、`msg`→`message` 等） |
| producer | `worker_py/producer.py` | 写入 `trace:persist` |
| log | `worker_py/log.py` | 结构化日志；带 `trace_id` |

**禁止**：Python Worker 直接写 SQLite。

### 2.3 worker（Go Worker，必须）

| 模块 | 路径（规划） | 职责 |
|------|--------------|------|
| main | `worker/cmd/worker/main.go` | 启动、信号、graceful shutdown |
| config | `worker/internal/config` | YAML/env；消费 `trace:persist` |
| consumer | `worker/internal/consumer` | XREAD GROUP / BRPOP |
| writer | `worker/internal/writer` | 批量写 SQLite（WAL） |
| cache | `worker/internal/cache` | 写后 DEL/SETEX `trace:{id}` |
| metrics/log | `worker/internal/log` | 结构化日志；队列深度告警 |

### 2.4 frontend（Vue3）

单页：输入框 + 时间线列表 + 空态/错误态。

---

## 3. API 详细

### 3.1 POST `/api/v1/logs/ingest`

**请求（批量）**

```json
{
  "logs": [
    {
      "trace_id": "550e8400-e29b-41d4-a716-446655440000",
      "span_id": "a1b2c3d4e5f67890",
      "service": "gateway",
      "level": "INFO",
      "message": "request handled",
      "timestamp": "2026-09-27T22:00:00+08:00",
      "fields": { "method": "POST", "path": "/api/v1/projects" }
    }
  ]
}
```

**成功响应**

```json
{ "code": 0, "message": "ok", "data": { "accepted": 1 } }
```

**错误码**

| code | HTTP | 含义 |
|------|------|------|
| 0 | 200 | 成功入队 |
| 40001 | 400 | 校验失败（缺 trace_id 等） |
| 50301 | 503 | 队列超软上限 / Redis 不可用 |
| 50000 | 500 | 未预期错误 |

**行为**：轻量校验 → Redis `trace:ingest` 入队 → 返回；**禁止**在此路径 `INSERT` SQLite；深度规范化交给 Python Worker。

### 3.2 GET `/api/v1/logs?trace_id=<uuid>`

**成功**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "trace_id": "550e8400-e29b-41d4-a716-446655440000",
    "logs": [
      {
        "id": 1,
        "trace_id": "550e8400-e29b-41d4-a716-446655440000",
        "span_id": "a1b2c3d4e5f67890",
        "service": "gateway",
        "level": "INFO",
        "message": "request handled",
        "timestamp": "2026-09-27T22:00:00+08:00",
        "fields": {}
      }
    ]
  }
}
```

无数据：`logs: []`。缺参：40001。

**行为**：`GET cache:trace:{id}` → 命中返回；否则 `SELECT ... WHERE trace_id=? ORDER BY timestamp ASC` → `SETEX` TTL 60s。

### 3.3 GET `/healthz`

```json
{ "status": "ok" }
```

可选（可复议）增加 `queue_depth`、`worker_heartbeat`。

---

## 4. 表结构 DDL（SQLite）

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;

CREATE TABLE IF NOT EXISTS logs (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  trace_id     TEXT    NOT NULL,
  span_id      TEXT,
  service      TEXT    NOT NULL,
  level        TEXT    NOT NULL,
  message      TEXT    NOT NULL,
  timestamp    TEXT    NOT NULL,
  fields_json  TEXT,
  created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_logs_trace_id ON logs(trace_id);
CREATE INDEX IF NOT EXISTS idx_logs_trace_ts ON logs(trace_id, timestamp);
```

说明：写入**仅 Worker**；API 进程只用只读连接查询（可复议共享路径但避免多写）。

---

## 5. 校验规则

| 规则 | 处理 |
|------|------|
| 缺 `trace_id`/`service`/`level`/`message`/`timestamp` | 整单或该条 400；批量可跳过非法条并返回 accepted=成功数（**默认整批失败更简单，可复议部分成功**） |
| `level` 大小写 | 入库前规范化为大写 |
| `msg` 别名 | 接受 `msg` → 映射 `message` |
| `fields` 非 object | 400 |
| 单批最大条数 | 默认 500（可复议） |

---

## 6. 并发、写入与峰值策略

### 6.1 数据流（ascii）

```
+-------------+  timeout=200ms  +-----------+  XADD   +----------------+
| 业务 async  |---------------->|  FastAPI  |-------->| Redis          |
+-------------+  fail=drop      |  ingest   |         | trace:ingest   |
                                +-----------+         +--------+-------+
                                                               |
                                                          XREAD|
                                                               v
                                                      +----------------+
                                                      | Python Worker  |
                                                      | normalize/enrich|
                                                      +--------+-------+
                                                               | XADD
                                                               v
                                                      +----------------+
                                                      | Redis          |
                                                      | trace:persist  |
                                                      +--------+-------+
                                                               |
                                                          XREAD|
                                                               v
                                                      +----------------+
                                                      | Go Worker      |
                                                      +--------+-------+
                                                               | batch INSERT
                                                               v
                                                      +----------------+
                                                      | SQLite WAL     |
                                                      +----------------+
```

### 6.2 策略表

| 项 | 默认 |
|----|------|
| 业务侧 | 异步；短超时；失败丢弃 |
| ingest | 只入 `trace:ingest` |
| Python Worker | 规范化后入 `trace:persist`；不写 SQLite |
| Go Worker 批量 | 默认每批 50–200 条或 100ms 刷盘（可配置） |
| SQLite | WAL；busy_timeout=5000；单 Writer=**Go Worker** |
| 背压 | `LLEN`/`XLEN` > 100000 → ingest 50301 |
| 限流 | 可选 Redis 固定窗口（如 5000 req/s/IP）；默认关 |
| 缓存失效 | Worker 写入涉及的 `trace_id` 执行 `DEL trace:{id}`；或直接重载预热 |
| graceful shutdown | Worker 处理完当前批再退出；API 停止接流 |

---

## 7. 前端信息架构（线框文字）

```
+--------------------------------------------------+
|  traceService                    [健康: ok]       |
+--------------------------------------------------+
|  Trace ID: [________________________]  [查询]    |
+--------------------------------------------------+
|  时间线                                          |
|  22:00:00.010  gateway   INFO   request start    |
|  22:00:00.025  user-svc  INFO   auth ok          |
|  22:00:00.080  ai-svc    INFO   job running      |
|  22:00:00.120  ai-svc    ERROR  mock fail ...    |
+--------------------------------------------------+
|  空态：未查询 / 无数据请检查 Worker 是否追上     |
|  错误态：红色横幅显示 message                    |
+--------------------------------------------------+
```

一页式；无需路由（可复议加 history）。

---

## 8. 配置项清单

### 8.1 backend `configs/default.yaml`

```yaml
server:
  host: "127.0.0.1"
  port: 8100
redis:
  addr_env: REDIS_ADDR      # 默认 127.0.0.1:6379
  password_env: REDIS_PASSWORD
  ingest_queue_key: "trace:ingest"
  persist_queue_key: "trace:persist"   # API 不消费；仅文档对齐
  queue_type: "stream"       # stream | list
  cache_prefix: "trace:"
  cache_ttl_sec: 60
  queue_soft_limit: 100000
sqlite:
  path: "./data/logs.db"    # API 只读打开同一文件
cors:
  origins:
    - "http://127.0.0.1:5174"
    - "http://localhost:5174"
ingest:
  max_batch: 500
```

### 8.2 worker_py `configs/default.yaml`

```yaml
redis:
  addr_env: REDIS_ADDR
  ingest_queue_key: "trace:ingest"
  persist_queue_key: "trace:persist"
  queue_type: "stream"
  group: "trace-ingest-workers"
  consumer: "py-worker-1"
normalize:
  max_batch: 100
  flush_interval_ms: 50
```

### 8.3 worker（Go）`configs/default.yaml`

```yaml
redis:
  addr_env: REDIS_ADDR
  queue_key: "trace:persist"
  queue_type: "stream"
  group: "trace-persist-workers"
  consumer: "go-worker-1"
sqlite:
  path: "./data/logs.db"
  busy_timeout_ms: 5000
  batch_size: 100
  flush_interval_ms: 100
cache:
  prefix: "trace:"
  # 写后策略: delete | refresh ；默认 delete
  invalidate_mode: "delete"
```

---

## 9. 扩展点

| 扩展 | 说明 |
|------|------|
| PostgreSQL | 标可复议；MVP 不做；换 writer 方言与 DSN |
| span 树 | 用 `span_id`/`parent_span_id` 后续渲染 |
| auth | 网关共享 token 或 mTLS |
| 合并双 Worker | 可复议；MVP 保持 FastAPI + Python Worker + Go Worker |
| OTLP 导出 | Worker 旁路 |

---

## 10. 与主仓 AGENTS.md 对齐检查表

- [ ] `trace_id` 字段名与 `X-Trace-Id` 一致
- [ ] 日志必填字段与 §D.2 一致
- [ ] 主仓不 import traceService
- [ ] 主业务 MySQL / trace SQLite（§J）
- [ ] 上报异步不阻塞（§D.3 / §I）
- [ ] 两级队列 + 双 Worker（§K）
- [ ] 错误体 `{code,message,data}` 风格一致
- [ ] 密钥走 env，不入库

---

## 11. 目录规划（含 worker_py + worker）

```
traceService/
├── README.md
├── .gitignore
├── docs/           # PRD DESIGN ARCHITECTURE PLAN TODO README
├── backend/        # FastAPI API
├── worker_py/      # Python Worker（必须）
│   ├── main.py / worker/
│   ├── requirements.txt
│   └── configs/default.yaml
├── worker/         # Go Worker module（必须）
│   ├── go.mod
│   ├── cmd/worker/main.go
│   ├── internal/...
│   └── configs/default.yaml
└── frontend/       # Vue3
```
