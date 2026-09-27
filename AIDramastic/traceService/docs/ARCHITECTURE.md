# traceService 架构说明（ARCHITECTURE）

| 字段 | 内容 |
|------|------|
| 文档版本 | v0.3 |
| 日期 | 2026-09-27 |
| 路径 | `traceService/docs/ARCHITECTURE.md`（保持可被 GitHub blob 打开） |
| 关联 | `PRD.md` / `DESIGN.md` / `PLAN.md`；根 `AGENTS.md` §D/§I/§J/**§K** |

---

## 1. 背景：为何独立架构

主仓 Go 微服务以 **MySQL** 承载业务重状态；联调需要按 `trace_id` 查跨进程日志，但不希望：

1. 给主路径增加同步 IO；
2. 强迫开发者先起 Jaeger/ELK；
3. 让日志写入与业务事务争用 MySQL。

因此 **traceService** 独立进程族：轻量 **SQLite** 持久化 + **Redis** 两级队列削峰 + **FastAPI** 接入查询 + **Python Worker** 规范化 + **Go Worker** 专责写入。

---

## 2. 系统上下文（C4 Context）

```
                    +----------------------+
                    |  开发者 / Agent /    |
                    |  联调同学            |
                    +----------+-----------+
                               | 浏览器
                               v
+--------------+      +--------+---------+      +------------------+
| 主业务 Web   |      | traceService Web |      |  mock 脚本       |
| (Vue3)       |      | (Vue3)           |      |  gen_mock_logs   |
+------+-------+      +--------+---------+      +--------+---------+
       |                       |                         |
       | HTTP+JWT              | HTTP query              | HTTP ingest
       v                       v                         v
+------+-----------------------+-------------------------+------+
|                     主业务集群 (Go)                            |
|  gateway / user-svc / drama-svc / ai-svc   库: MySQL         |
|  Redis: JWT黑名单等                                            |
+------+---------------------------------------------------+---+
       | 异步 ingest (不阻塞)
       v
+------+-------------------------------------------------------+
|                     traceService                             |
|  FastAPI + Python Worker + Go Worker + Redis + SQLite        |
+--------------------------------------------------------------+
```

---

## 3. 容器图（C4 Container）

```
+------------------ traceService --------------------------------+
|                                                                |
|  +-------------+  XADD ingest  +----------------------------+  |
|  | FastAPI     |-------------->| Redis                      |  |
|  | :8100       |               | trace:ingest / persist     |  |
|  | ingest/query|<--------------| + query cache              |  |
|  +------+------+   get/set     +------+-------------+-------+  |
|         | read-only                   |             |          |
|         |                    consume  |             | consume  |
|         |                             v             v          |
|         |                    +--------+----+  +-----+--------+ |
|         |                    | Python      |  | Go Worker    | |
|         |                    | Worker      |  | batch write  | |
|         |                    | (normalize) |  +------+-------+ |
|         |                    +------+------+         |         |
|         |                           | XADD persist   |         |
|         v                           +----------------+         |
|  +------+------+                                               |
|  | SQLite      |<---------- only Go Worker writes ------+      |
|  | logs.db     |                                               |
|  +-------------+                                               |
|                                                                |
|  +-------------+                                               |
|  | Vue3 :5174  |---- GET /api/v1/logs ------------------------>|
|  +-------------+                                               |
+----------------------------------------------------------------+

上报方：gateway / user-svc / drama-svc / ai-svc / mock script
```

| 容器 | 技术 | 职责 |
|------|------|------|
| API | Python FastAPI | 轻量校验、入 `trace:ingest`、查询、health、CORS |
| Python Worker | **Python** | 消费 `trace:ingest` → 规范化/enrich → 入 `trace:persist` |
| Go Worker | **Go** | 消费 `trace:persist`、批量写 SQLite、缓存维护 |
| Web | Vue3 | 时间线 UI |
| Redis | Redis | 两级队列 + 查询缓存 + 可选限流 |
| SQLite | 文件 DB | **唯一**日志持久化 |

---

## 4. 组件图（API + Python Worker + Go Worker）

### 4.1 FastAPI

```
main.py
  ├── routers: ingest / query / healthz
  ├── schemas: LogIn, IngestRequest, LogOut
  ├── services: RedisQueue.enqueue(trace:ingest), TraceCache.get/set
  └── db: sqlite3/aiosqlite **只读** 查询连接
```

### 4.2 Python Worker

```
worker_py/main.py
  ├── config.Load
  ├── consumer.Run (trace:ingest)
  ├── normalize.Enrich(batch)
  ├── producer.Enqueue(trace:persist)
  └── signal → graceful stop
```

### 4.3 Go Worker

```
cmd/worker/main.go
  ├── config.Load
  ├── consumer.Run (trace:persist；Stream 消费者组 或 List BRPOP)
  ├── writer.Flush(batch) → SQLite WAL
  ├── cache.Invalidate(traceIDs)
  └── signal.Notify → graceful stop
```

---

## 5. 序列图：一次带 trace_id 的请求如何产生多条日志并被查询

```
Web   gateway  ai-svc   FastAPI   Redis(ingest)  PyWorker  Redis(persist)  GoWorker  SQLite
 |       |        |        |           |            |            |            |        |
 |--tid->|        |        |           |            |            |            |        |
 |       |--rpc-->|        |           |            |            |            |        |
 |       |        |--async ingest----->|           |            |            |        |
 |       |        |        |--XADD---->|           |            |            |        |
 |       |        |        |<--ack-----|           |            |            |        |
 |<-resp-|        |        |           |            |            |            |        |
 |       |        |        |           |--XREAD---->|            |            |        |
 |       |        |        |           |            |--normalize-|            |        |
 |       |        |        |           |            |--XADD----->|            |        |
 |       |        |        |           |            |            |--XREAD---->|        |
 |       |        |        |           |            |            |            |--INSERT|
 |       |        |        |           |            |            |            |--DEL cache
 | 打开 trace Web，输入同一 trace_id
 |--GET /logs-------------->|           |            |            |            |        |
 |       |        |        |--cache miss--------------------------------------|-------->|
 |       |        |        |--SETEX cache-----------|            |            |        |
 |<-timeline----------------|           |            |            |            |        |
```

要点：业务响应在 ingest **入 `trace:ingest`** 后即可返回；规范化由 Python Worker、落库由 Go Worker 追赶。

---

## 6. 部署拓扑（本地）

```
终端1: redis-server                 (:6379)
终端2: uvicorn FastAPI              (:8100)
终端3: python -m worker (worker_py)
终端4: go run ./cmd/worker          (Go Worker)
终端5: pnpm dev 前端                (:5174)
可选:  MySQL（主业务，与 trace 无关）
```

API + 双 Worker + Redis + 前端即可验证闭环；无需 Docker 化 trace（可复议）。

---

## 7. 失败模式

| 失败 | 影响 | 约定 |
|------|------|------|
| Redis 宕机 | ingest 503；查询可降级直读 SQLite（可复议） | 主业务上报失败丢弃 |
| Python Worker 宕机 | `trace:ingest` 堆积；`persist` 暂无新消息 | 重启续消费 |
| Go Worker 宕机 | `trace:persist` 堆积；查询可能旧数据 | 重启续消费；监控队列深度 |
| SQLite busy | Go Worker 重试（busy_timeout） | 不在 API / Python Worker 写库 |
| FastAPI 宕机 | 无法新 ingest/查询 | 主业务仍可用 |
| 业务同步误调 ingest | **禁止**；规范与 code review 拦截 | AGENTS 强制异步 |

**核心约定**：ingest 失败**不影响**主业务 HTTP/gRPC 成功与否。

---

## 8. 安全与隐私

- 脱敏在上报方；本服务不做内容审计（MVP）。
- 默认绑定 `127.0.0.1`；无强鉴权（可复议）。
- DB 文件进 `.gitignore`；不含密钥。

---

## 9. 演进路线

| 阶段 | 内容 |
|------|------|
| M0 | 文档 + 目录（含 `worker_py/` + `worker/`） |
| M1 | FastAPI + Redis + Python Worker + Go Worker + SQLite + Web 闭环 |
| M2 | 限流、retention、部分成功批量、可选 OTLP 导出 |
| 可复议 | 合并双 Worker；SQLite→PostgreSQL（需改 AGENTS §J） |

---

## 10. 默认决策（架构）

| # | 决策 |
|---|------|
| A1 | 主业务 DB=**MySQL**；trace DB=**SQLite** |
| A2 | Redis：主业务缓存/黑名单；trace 缓冲+查询缓存 |
| A3 | **Python Worker + Go Worker + Redis 两级队列 + SQLite 持久化** |
| A4 | FastAPI / Python Worker 不做同步写 SQLite |
| A5 | 业务上报异步、短超时、失败可丢 |
| A6 | 队列：`trace:ingest` → Python Worker → `trace:persist` → Go Worker |

---

## 11. 并发与峰值（专节图）

```
突发 ingest
    |||||
    vvvvv
  FastAPI 快速入队 -----> Redis (软上限 1e5)
                            |
                     积压时背压 503
                            |
                            v
                     Go Worker 批量追赶
                            |
                            v
                     SQLite WAL 单写
                            |
  查询 QPS ----> Redis 热点缓存 ---- miss ----> SQLite 只读
```

压测建议（验收用）：对 ingest 持续推送，确认 (1) API p99 入队延迟达标 (2) 主业务接口延迟无显著抬升 (3) Worker 最终追平队列。
