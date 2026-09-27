# traceService 产品需求文档（PRD）

| 字段 | 内容 |
|------|------|
| 文档版本 | v0.3 |
| 日期 | 2026-09-27 |
| 状态 | 现行 / MVP |
| 负责人角色 | 开发者本人 / Agent（占位） |
| 关联 | `DESIGN.md` / `ARCHITECTURE.md` / `PLAN.md` / `TODO.md`；仓库根 `AGENTS.md` §D/§I/§J/**§K** |

---

## 1. 文档信息

本 PRD 定义独立可观测子系统 **traceService**：按 `trace_id` 接收、缓冲、持久化并查询跨服务结构化日志，提供简单 Web UI。  
**不**替代生产级 APM（Jaeger / ELK / 完整 OpenTelemetry 集群）。

---

## 2. 背景（细粒度）

### 2.1 为什么需要自研轻量 trace

AIDramastic 主业务为多进程 Go 微服务（gateway / user-svc / drama-svc / ai-svc）。一次「抽取章节资产」会跨 3–4 个进程。联调时常见问题：

- 只看单个进程日志无法还原顺序；
- 前端只看到 `{code,message}`，不知道卡在 ai job 还是 drama 写回；
- 引入 Jaeger/ELK 对个人/小团队过重，且阻塞脚手架节奏。

因此需要一个 **本地可起、协议简单、按 `trace_id` 出时间线** 的轻量服务。

### 2.2 与 Jaeger / ELK / OpenTelemetry 的关系

| 系统 | MVP | 未来 |
|------|-----|------|
| Jaeger / Tempo 等 | **不做** | 可复议：Worker 旁路导出 OTLP |
| ELK / Loki | **不做** | 可复议：SQLite 导出或双写 |
| OpenTelemetry SDK | **不做强制依赖** | 字段可向 OTel 语义靠拢（`trace_id`/`span_id`） |
| 本 traceService | **必做** | 保持独立进程与协议 |

### 2.3 为何 Python FastAPI + 双 Worker + 仓内子目录 + 不阻塞 Go 主业务

| 决策 | 理由 |
|------|------|
| 仓内 `traceService/` 子目录 | 与主仓协议（header/JSON）同仓演进；仍禁止主仓 `import` 其代码 |
| HTTP API 用 **FastAPI** | 接入与 query 快；与主仓 Go 解耦，主业务脚手架未就绪也能先做 |
| **Python Worker（必须）** | 消费 `trace:ingest`：校验/规范化/enrich；与 FastAPI 同生态，API 进程保持极薄 |
| **Go Worker（必须）** | 消费 `trace:persist`：高并发批量写 SQLite；SQLite 写入集中单进程 |
| 两级队列 | ingest 快速返回；规范化与落库解耦，互不拖死 |
| 不阻塞 Go 服务 | 主业务只异步 HTTP 上报；ingest 失败可丢；主路径零同步落库 |

### 2.4 目标用户

| 用户 | 场景 |
|------|------|
| 开发者本人 | 本地 mock 全链路，用 Web 粘贴 `trace_id` |
| Agent | 按 PLAN/TODO 实现与验收 |
| 联调同学 | gateway 报错时凭响应/`X-Trace-Id` 定位跨服务日志 |

### 2.5 存储分层（与主仓对齐，写死）

| 系统 | 持久化主库 | Redis |
|------|------------|-------|
| 漫剧主系统 | **MySQL** | 缓存/JWT 黑名单等（非业务主库） |
| **本服务** | **SQLite** | 两级队列（`trace:ingest` / `trace:persist`）+ 查询缓存 + 可选限流 |

禁止：把主业务表放到本服务 SQLite；MVP 把本服务主存储改成 MySQL（可复议，本阶段不做）。

---

## 3. 目标与非目标

### 3.1 目标

1. 接收单条/批量 JSON 日志（ingest），轻量校验后入 Redis **`trace:ingest`** 并立即返回。
2. **Python Worker** 消费 `trace:ingest`：校验/规范化/enrich → 入 **`trace:persist`**。
3. **Go Worker** 消费 `trace:persist`，批量写入 **SQLite**（WAL），维护按 `trace_id` 的查询缓存。
4. 按 `trace_id` 查询时间线（时间升序）；Web 可展示。
5. 健康检查；本地多进程可起（API + Python Worker + Go Worker + 前端）。
6. 业务侧上报约定：异步、短超时、失败可丢，**不阻塞**主请求。

### 3.2 非目标（MVP）

- 分布式采样、火焰图、全量指标、服务拓扑自动发现
- 强鉴权 / 多租户（本地默认无强鉴权，**可复议**）
- 主业务 MySQL 共享表
- 同步在 ingest 路径写 SQLite
- Jaeger Operator / K8s 依赖

---

## 4. 用户故事（≥4）

| ID | 故事 | 验收要点 |
|----|------|----------|
| US1 | 作为开发者，我用 mock 脚本推入同一 `trace_id` 的多服务日志，以便在 Web 看到时间线 | 脚本打印 trace_id；Web 列表按时间升序、多 service |
| US2 | 作为联调同学，gateway 返回错误时我复制 `X-Trace-Id`，在 trace Web 定位失败服务 | 能看到 ERROR 行及前后文 |
| US3 | 作为开发者，我批量 ingest 100 条，API 快速返回，不因 SQLite 锁卡住 | 响应时间与队列写入相关；Worker 异步落库 |
| US4 | 作为开发者，查询不存在的 `trace_id` 得到空列表而非 500 | HTTP 200 + `data: []` |
| US5 | 作为开发者，主业务在 traceService 宕机时仍能完成登录/建项目 | 上报超时/失败不影响主响应 |

---

## 5. 功能需求（FR）

| ID | 需求 | 优先级 |
|----|------|--------|
| FR1 | `POST /api/v1/logs/ingest`：单条对象或 `{logs:[...]}`；轻量校验后写 `trace:ingest`；立即返回 accepted | P0 |
| FR2 | `GET /api/v1/logs?trace_id=`：缓存优先，未命中查 SQLite 并回填；结果时间升序 | P0 |
| FR3 | `GET /healthz`：进程存活；可选暴露两级队列深度（可复议） | P0 |
| FR4a | **Python Worker**：消费 `trace:ingest` → 校验/规范化/enrich → 入 `trace:persist` | P0 |
| FR4b | **Go Worker**：消费 `trace:persist`、批量 INSERT SQLite、缓存失效/预热 | P0 |
| FR5 | Vue3 Web：输入 trace_id、展示时间线、空态/错误态 | P0 |
| FR6 | 可选 retention：按天删除旧日志或限制 DB 大小（默认可手工删文件，**可复议**自动化） | P2 |
| FR7 | 可选限流：Redis 固定窗口保护 ingest | P2 |
| FR8 | 可选 mock 脚本 `gen_mock_logs.py` | P1 |

---

## 6. 非功能需求（NFR）与并发峰值

### 6.1 延迟与容量（MVP 单机目标）

| 指标 | 目标（默认，可复议） |
|------|----------------------|
| ingest p99（入队返回） | ≤ 50ms（本机 Redis 可达时） |
| 查询 p99（缓存命中） | ≤ 30ms |
| 查询 p99（缓存未命中） | ≤ 200ms（十万级行内） |
| 持久化容量 | 单机 **十万级** 日志行够用 |
| 突发 ingest | 队列可短暂堆积；Worker 批量追赶；超阈值背压 |
| 队列软上限 | 默认 100000 条（可配置）；超限 ingest 返回 503 |

### 6.2 并发与峰值（专节）

```
业务请求路径（必须快）
  └─ 打日志 ─► 异步 client ─► HTTP ingest (timeout 200ms)
                    │ 失败：丢弃 / Warn
                    ▼
              FastAPI ingest
                    │ 轻量校验
                    │ XADD `trace:ingest`   ← 唯一同步 IO（快）
                    ▼
              立即 200 {accepted:N}     ← 绝不 sqlite3_step

两级峰值缓冲
  Redis `trace:ingest`
        │
        ▼
  Python Worker（校验/规范化/enrich）
        │
        ▼
  Redis `trace:persist`
        │
        ▼
  Go Worker（批量 XREAD）
        ├─ BEGIN; 多行 INSERT; COMMIT
        ├─ SQLite WAL + busy_timeout
        └─ DEL/SET 查询缓存 trace:{id}

查询路径
  GET ?trace_id= ─► Redis GET ─命中► 返回
                      │未命中
                      ▼
                    SQLite SELECT ORDER BY timestamp
                      │
                      └─ SETEX 缓存 TTL=60s ─► 返回
```

| 规则 | 默认决策 |
|------|----------|
| 业务侧 | fire-and-forget；超时 200ms；失败可丢 |
| ingest | 只入 `trace:ingest`；不做同步落库 |
| Python Worker | 规范化后入 `trace:persist`；**不**写 SQLite |
| SQLite 写入 | **仅 Go Worker**；单写多读；WAL；busy_timeout=5000ms |
| 限流 | 可选；默认先做队列长度背压 |
| Worker 崩溃 | 消息留在对应 Redis 队列；重启后续消费（至少一次）；注意幂等 |

### 6.3 安全

- 本地 MVP：**无强鉴权**（可复议：共享 token / 仅绑定 127.0.0.1）
- 脱敏责任在**上报方**（密码/JWT/密钥不得出现在 message/fields）
- CORS：放开本地 Vite origin

---

## 7. 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/logs/ingest` | 入队 |
| GET | `/api/v1/logs?trace_id=` | 查询时间线 |
| GET | `/healthz` | 健康检查 |

错误体风格与主仓对齐：`{ "code", "message", "data" }`（0=成功）。

---

## 8. 日志 JSON Schema（完整字段表）

| 字段 | 必填 | 类型 | 示例 | 说明 |
|------|------|------|------|------|
| `trace_id` | 是 | string (UUID) | `550e8400-e29b-41d4-a716-446655440000` | 全链路 ID |
| `service` | 是 | string | `gateway` | 服务名 |
| `level` | 是 | string | `INFO` | DEBUG/INFO/WARN/ERROR |
| `message` | 是 | string | `request handled` | 也接受 `msg`，入库统一 `message` |
| `timestamp` | 是 | string 或 number | `2026-09-27T22:00:00+08:00` | ISO8601 优先；Unix 秒可复议接受 |
| `span_id` | 否 | string | `a1b2c3d4e5f67890` | 单步 ID |
| `fields` | 否 | object | `{"method":"POST","user_id":"u1"}` | 扩展字段；入库 `fields_json` |

Ingest 请求：

```json
{ "logs": [ { "trace_id":"...", "service":"gateway", "level":"INFO", "message":"ok", "timestamp":"2026-09-27T22:00:00+08:00" } ] }
```

也可直接 POST 单条对象（实现须兼容）。

成功响应：

```json
{ "code": 0, "message": "ok", "data": { "accepted": 1 } }
```

---

## 9. 验收标准

- [ ] 不依赖 Jaeger/ELK 即可完成 ingest → Python Worker → Go Worker 落库 → query → Web
- [ ] ingest 返回时 SQLite 可不含新行（异步），最终一致可见
- [ ] 主业务在 API/任一 Worker/Redis 异常时仍可响应（上报失败不影响）
- [ ] 同一 `trace_id` 多 service 时间线升序正确
- [ ] 空 `trace_id` 查询 → 空列表
- [ ] 文档、目录含 `worker_py/` 与 `worker/`；技术栈表同时含 Python Worker 与 Go Worker
- [ ] 存储：仅 SQLite 持久化日志；未引入 MySQL 作 trace 主库

---

## 10. 文档索引

| 文档 | 用途 |
|------|------|
| `DESIGN.md` | 模块、API 示例、DDL、配置、扩展点 |
| `ARCHITECTURE.md` | C4、序列图、失败模式、演进 |
| `PLAN.md` | 带 checkbox 的开发任务（含 Python Worker + Go Worker） |
| `TODO.md` | 更碎的执行清单 |
| `README.md`（本 docs） | 索引 |
| `../README.md` | 子系统总览与启动 |
| `../../AGENTS.md` | 宪法 §D/§I/§J/**§K** |

---

## 11. 默认决策表

| # | 决策 | 可复议 |
|---|------|--------|
| T1 | 持久化 **SQLite** | MVP 否 |
| T2 | 缓冲/缓存 **Redis** | MVP 否 |
| T3 | API **FastAPI**；**Python Worker** + **Go Worker** | 双 Worker 写死；语言细节可复议 |
| T4 | ingest → `trace:ingest` → Python Worker → `trace:persist` → Go Worker → SQLite | 否 |
| T5 | 查询 Redis → SQLite → 回填 | 否 |
| T6 | 业务上报异步不阻塞 | 否 |
| T7 | Redis 默认 Stream（可改 List） | 是 |
| T8 | 本地无强鉴权 | 是 |
| T9 | 缓存 TTL 60s | 是 |
| T10 | 队列软上限 1e5；超限 503 | 是 |
| T11 | Python Worker 不写 SQLite；Go Worker 为唯一写者 | 否 |
| T12 | 目录：`backend/` + `worker_py/` + `worker/` + `frontend/` | 否 |
