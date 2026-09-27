# AGENTS.md — AIDramastic 编码与工程宪法

> 给 **Cursor / AI Agent / 人类** 直接遵守的规则。条目可执行；细节与示例见 `docs/prd-20260927-init-service/CODING_STANDARDS.md`。  
> **冲突时**：产品级约定（trace_id、可插拔 AI、错误不 panic、与 traceService 边界、**队列与 Worker**）以**本文件**优先说明；实现细节以本文件 + CODING_STANDARDS 为准。

---

## A. 总则

1. 技术形态：**Go 微服务**（gateway HTTP BFF + user/drama/ai gRPC）+ **Vue3** 主前端。
2. 业务错误**只** `return error`，**禁止**用 panic 做控制流；库代码禁止 panic。
3. 配置使用 **YAML**，支持**热更新**；解析/校验失败必须保留旧配置并打 Error 日志。
4. AI 能力按 YAML 的 `element_type` / `capacity` / `driver` **可插拔**注册；业务只调 Provider 接口，禁止把厂商 SDK 写死在 service 层。
5. MVP 阶段真实 AI / 支付 / 完整 APM **不做**；mock/stub + 规范 + 可观测约定先行。
6. **重活必须入队**：凡外部 IO / 长耗时 / Provider 调用（含 mock）一律走 **Redis 队列 + Worker**；禁止在 handler/service 同步执行（见 **§K**）。

---

## B. 错误处理（定死）

1. 业务路径：只 `return error`（或包装后的 error）向上传。
2. **禁止**在 `app/shared/**`、`internal/**` 内 `panic`；禁止用 panic 做分支。
3. 仅 `main` 启动阶段：致命配置/依赖失败允许 `log.Fatal` / `os.Exit(1)`。
4. 统一业务错误类型 `BizError{Code int, Message string}`（见 `app/shared/errors`）。
5. Handler 负责映射：
   - gRPC：`status` + 业务 detail（码段见 PRD / CODING_STANDARDS）
   - HTTP（gateway）：统一体 `{ "code", "message", "data" }`
6. 未知 error → 500 / Internal，**必须打日志**，不得把 stack 明文返回客户端。

---

## C. 分层

```
handler (gRPC/HTTP) → service → repo
                         ↘ adapter（第三方 / AI Provider）
                         ↘ queue（入 Redis；由独立 Worker 消费）
```

| 层 | 职责 | 禁止 |
|----|------|------|
| handler | 参数校验、鉴权提取、DTO/proto 转换、错误映射 | SQL、调外部 AI、同步跑 Provider |
| service | 业务编排、事务、状态机、**创建 job + 入队** | 直连厂商 SDK；同步调 Provider 重逻辑 |
| repo | MySQL / Redis | 调外部 HTTP AI、依赖 service |
| adapter | AI driver、外部客户端；注册到 Registry | 反向依赖 handler；在 API 进程内被同步调用重逻辑 |
| worker | 消费 Redis 队列、执行 Provider / 落库 | 对外暴露 HTTP/gRPC 业务入口（与 API 进程分离） |

禁止 handler 直访 DB；禁止 repo 依赖 service。Provider 实现一律放 **adapter**，由 **Worker 进程**调用。

---

## D. 可观测性（重点）

### D.1 trace_id 强制

1. 每个 HTTP / gRPC 请求**必须**有 `trace_id`（UUID 字符串）。
2. 客户端可传请求头 `X-Trace-Id`；**没有则由 gateway / 入口服务生成**。
3. 向下游透传：
   - gRPC metadata：`trace_id`（及 `x-user-id`）
   - HTTP header：`X-Trace-Id`（及用户身份相关头，按 gateway 约定）
4. 入口中间件写入 context；出站客户端从 context 读出并注入。
5. Job / 队列消息必须带 `trace_id`（及 `job_id`）；Worker 日志同样强制带上。

### D.2 结构化日志字段（每条必带）

| 字段 | 说明 |
|------|------|
| `trace_id` | 全链路 ID |
| `service` | 服务名，如 `gateway` / `user-svc` / `ai-worker` / `trace-api` / `trace-worker-py` / `trace-worker-go` |
| `level` | DEBUG / INFO / WARN / ERROR |
| `msg` / `message` | 日志正文 |
| 时间 | ISO8601 或 Unix；推荐带时区，如 `2026-09-27T22:00:00+08:00` |

推荐：**JSON 一行一条**。可选：`span_id`、`user_id`、`method`、`err`、`job_id`、自定义 `fields`。

### D.3 日志如何进入 traceService（默认定死 · 双 Worker 两级队列）

**默认（MVP）**：各服务将 JSON 日志通过 HTTP **异步**推到 traceService（短超时、失败可丢，不阻塞主路径）：

```
业务服务 async POST /api/v1/logs/ingest
    → FastAPI：轻量校验 → 入 Redis 队列 `trace:ingest` → 立即返回
    → Python Worker：消费 `trace:ingest` → 校验/规范化/enrich → 入 `trace:persist`
    → Go Worker：消费 `trace:persist` → 批量写 SQLite（WAL）+ 更新 Redis 查询缓存
    → FastAPI query：Redis cache → SQLite
```

- 技术栈写死：**FastAPI API + Python Worker + Go Worker + Vue3 + Redis + SQLite**
- 目录：`traceService/backend/`（API）、`traceService/worker_py/`（Python Worker）、`traceService/worker/`（Go Worker）、`traceService/frontend/`
- 本地开发也可用：写到约定目录 + 文件尾随采集（非默认；见 `traceService/docs/PLAN.md`）

禁止「必须先起 Jaeger / ELK 才能开发」。**traceService 可独立先做**，不阻塞主业务服务脚手架。

### D.4 查日志

打开 **traceService Web**，输入 `trace_id`，查看跨服务日志时间线（按时间排序）。

### D.5 脱敏

密码、JWT 全文、密钥、DSN 密码、用户隐私正文：**不得**明文落日志。

---

## E. 配置

1. 各服务独立 YAML（示例放仓库根 `configs/*.yaml` 或 `configs/*.example.yaml`）。
2. 热更：`Load` + `Watch`；成功则原子替换快照；失败保留旧值。
3. 密钥字段只写 **env 名**（如 `secret_env: JWT_SECRET`），程序 `os.Getenv`；禁止提交真实密钥。
4. AI providers 热更失败时保留旧 Registry。
5. Worker 与 API **可共用同一份配置文件的不同段落**，或独立 `*-worker.yaml`；队列 key / consumer group 必须显式配置。

---

## F. Proto

1. **先改** `protocol/**/*.proto`，再执行 `make gen`（或仓库规定脚本）。
2. **禁止手改** `*.pb.go` / `*_grpc.pb.go`。
3. 包名：`aidramastic.<domain>.v1`；RPC 名 VerbNoun。

---

## G. 前端（主业务 web）

1. Vue3 + Vue Router + Pinia；HTTP 客户端默认 Axios。
2. API 错误体约定：`{ code, message, data }`。
3. 请求头必须带：
   - `Authorization: Bearer <token>`（需登录接口）
   - `X-Trace-Id: <uuid>`（每次请求；可本地生成并贯穿一次用户操作）
4. 环境变量用 `VITE_*`；不把密钥写进前端仓库。

---

## H. 安全

1. 不提交：`.env`、真实密钥、`*.pem`、生产 DSN、secrets/。
2. 日志脱敏（见 D.5）。
3. 下游服务信任内网仍建议透传并校验 `x-user-id`（MVP 可简化，但接口先留好）。

---

## I. 与 traceService 的关系

1. `traceService/` 是**独立子系统**，技术栈定死：**FastAPI（API）+ Python Worker + Go Worker + Vue3 + Redis + SQLite**，可单独开发联调。
2. 主仓业务服务只通过**约定协议**上报日志（HTTP ingest 或文件约定）；**禁止** `import` traceService 源码。
3. 主业务 Go 服务未就绪时，也可先用模拟脚本往 traceService ingest，验证查询 Web。
4. 不把完整 APM / Jaeger 集群当作 MVP 依赖。
5. 存储边界见 **§J**：主业务 **MySQL**；trace **SQLite**（Redis 做队列缓冲/缓存）。
6. 目录定死：
   - `traceService/backend/` — FastAPI API（ingest 入队 + query）
   - `traceService/worker_py/` — **Python Worker**（消费 `trace:ingest` → 规范化 → 入 `trace:persist`）
   - `traceService/worker/` — **Go Worker**（消费 `trace:persist` → 批量写 SQLite + 缓存）
   - `traceService/frontend/` — Vue3
7. SQLite **写入只在 Go Worker**；FastAPI ingest **只**入 Redis `trace:ingest`；Python Worker **不**直接写 SQLite。
8. 队列与 Worker 总则见 **§K**。

---

## J. 存储约定（写死）

| 系统 | 持久化主库 | Redis 用途 | 禁止 |
|------|------------|------------|------|
| **漫剧主系统**（gateway / user / drama / ai） | **MySQL** | **队列**（`ai:jobs` 等）、JWT 黑名单、热点缓存；**不是**业务主库 | 主业务表落到 SQLite；用进程内 goroutine 替代默认队列 |
| **traceService** | **SQLite** | 两级队列（`trace:ingest` / `trace:persist`）、按 `trace_id` 查询缓存、可选限流 | MVP 把 trace 主存储改成 MySQL（标可复议，本阶段不做） |

补充：

1. 主业务：用户/项目/章节/分镜/assets/`ai_jobs` 等一律 MySQL。
2. traceService：日志只持久化到 SQLite；写入**仅**由 **Go Worker** 批量完成（WAL + busy_timeout）。
3. traceService 架构定死：**FastAPI API + Python Worker + Go Worker + Redis + SQLite**（两级队列）。
4. 业务服务上报日志：异步、短超时、失败可丢，**绝不阻塞**主请求路径。
5. 漫剧 ai-svc：API 进程只写 MySQL job + 入 Redis；Provider 执行只在 **Go Worker**。

---

## K. 队列与 Worker（强制）

> **本章写死**：Go 域与 Python 域**都**采用 Worker，**都**有 Redis 队列。重活禁止在 API/handler 同步跑。

### K.1 总则

1. **重活必须入队**：外部 IO、长耗时、AI Provider（**含 mock**）、批量落库、日志规范化/enrich —— 一律 Redis 队列 + 独立 Worker 进程。
2. **可复议例外**：user/drama 等**轻量 CRUD**（纯 MySQL 读写、毫秒级）可在 API 进程同步完成。
3. API 进程职责：校验 → 落轻量状态（如 MySQL job 行）→ **入队** → 立即返回 job_id/accepted；**禁止**在 handler/service 同步调 Provider 重逻辑。
4. Worker 与 API **进程分离**（独立 `main` / 独立部署单元）；不得把「开个 goroutine 当默认架构」。
5. 建议队列形态：**Redis Stream**（可复议 List）；消息必须可 JSON 序列化，带 `trace_id`、`job_id`（若有）。
6. **幂等 / 重试 / 死信**：消费至少一次；按 `job_id` 或消息 id 幂等；失败有限次重试后进死信（Stream 可用独立 dead letter stream / 字段标记，可复议实现细节）。
7. 日志强制带 `trace_id`；有 job 时带 `job_id`；Worker `service` 名与 API 区分（如 `ai-worker` vs `ai-svc`）。

### K.2 漫剧主系统（Go）— ai-svc

| 进程 | 目录约定 | 职责 |
|------|----------|------|
| **API** | `app/application/ai-svc/cmd/server` | 创建 `ai_jobs`（MySQL）、入 Redis 队列（建议 Stream `ai:jobs`）、`GetJob`/`ListJobs` 查状态 |
| **Go Worker** | `app/application/ai-svc/cmd/worker` | 消费 `ai:jobs` → Provider Registry 执行 → 回写 MySQL job 状态/`result_json` |

- Redis = **队列 + 缓存 + JWT 黑名单**（JWT 黑名单主要在 user/gateway；ai 侧重队列与可选锁）。
- **禁止** API 进程内「同进程 goroutine worker」作为默认实现（哪怕 mock 也走队列）。
- Job 锁建议：`ai:job:lock:{job_id}`（见 CODING_STANDARDS）。

### K.3 traceService — 两级队列 + 双 Worker

```
FastAPI ingest
    → Redis `trace:ingest`          （立即返回）
Python Worker（worker_py/）
    → 校验 / 规范化 / enrich
    → Redis `trace:persist`
Go Worker（worker/）
    → 批量写 SQLite（WAL）
    → 更新 / 失效 Redis 查询缓存
FastAPI query
    → Redis cache → SQLite
```

| 进程 | 目录 | 队列 | 职责 |
|------|------|------|------|
| FastAPI API | `traceService/backend/` | 生产 `trace:ingest` | ingest 入队、query、health |
| **Python Worker** | `traceService/worker_py/` | 消费 `trace:ingest`；生产 `trace:persist` | 校验/规范化/enrich |
| **Go Worker** | `traceService/worker/` | 消费 `trace:persist` | 批量写 SQLite + 缓存维护 |
| Vue3 | `traceService/frontend/` | — | 时间线 UI |

技术栈表必须写：**FastAPI API + Python Worker + Go Worker + Vue3 + Redis + SQLite**。

### K.4 目录速查

```
app/application/ai-svc/
  cmd/server/main.go      # API
  cmd/worker/main.go      # Go Worker
  internal/...

traceService/
  backend/                # FastAPI API
  worker_py/              # Python Worker
  worker/                 # Go Worker
  frontend/               # Vue3
```

### K.5 检查清单（队列相关，改代码前必扫）

- [ ] 重活是否入队？handler/service 是否仍同步调 Provider？
- [ ] ai-svc 是否同时有 `cmd/server` 与 `cmd/worker`？
- [ ] mock Provider 是否也走 Worker（未走同步捷径）？
- [ ] trace 是否两级队列（`trace:ingest` → Python Worker → `trace:persist` → Go Worker）？
- [ ] 消息与 Worker 日志是否带 `trace_id` / `job_id`？
- [ ] 是否有幂等键、有限重试与死信约定？
- [ ] API 与 Worker 是否进程分离（不是默认进程内 goroutine）？

---

## 快速检查清单（改代码前扫一眼）

- [ ] 错误是 return，不是 panic？
- [ ] 请求有 `trace_id` 且向下透传？
- [ ] 日志 JSON 含 `trace_id` + `service` + `level` + `msg` + 时间？
- [ ] 改了 proto 是否只改源文件并 gen？
- [ ] AI 新厂商是否只加 driver + yaml，未污染 service？
- [ ] 有无密钥进仓库 / 进日志？
- [ ] 主业务是否只用 MySQL（未误用 SQLite）？trace 是否只用 SQLite 持久化？
- [ ] 业务侧日志上报是否异步且不阻塞主路径？
- [ ] **重活是否走 Redis 队列 + Worker（见 §K）？Go 与 Python 是否都有 Worker？**
- [ ] **ai-svc / trace 目录是否含 server+worker（及 worker_py）？**
