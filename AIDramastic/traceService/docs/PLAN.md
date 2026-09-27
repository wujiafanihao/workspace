# traceService 开发计划（PLAN）

> 风格：Goal / Architecture / Tech / Constraints + checkbox Tasks。  
> **背景**：主业务多进程联调需要按 `trace_id` 查链，但不引入 Jaeger/ELK，也不阻塞 Go 脚手架。本子系统定死：**FastAPI（ingest 入队 + query）+ Python Worker（规范化）+ Go Worker（消费写库）+ Redis（两级队列/缓存）+ SQLite（持久化）**。主业务库是 **MySQL**（与本服务无关）；业务侧日志上报必须异步、短超时、失败可丢。详见 `PRD.md` / `ARCHITECTURE.md` / 根 `AGENTS.md` §J / **§K**。

---

## Goal

提供可独立运行的轻量日志检索服务：业务或 mock 上报 JSON → `trace:ingest` → Python Worker → `trace:persist` → Go Worker 落 SQLite → Web 按 `trace_id` 看跨服务时间线。

## Architecture（摘要）

```
业务 / mock --async POST--> FastAPI ingest --> Redis `trace:ingest`
                                                      |
                                              Python Worker (normalize)
                                                      |
                                                      v
                                              Redis `trace:persist`
                                                      |
                                              Go Worker
                                                      |
                                                      v
                                                   SQLite (WAL)
                                                      ^
Vue3 <-- GET -- FastAPI query (Redis cache -> SQLite)
```

详见 `ARCHITECTURE.md`。

## Tech Stack

| 层 | 选型 |
|----|------|
| API | Python 3.11+、FastAPI、uvicorn、Pydantic |
| Python Worker | **Python 3.11+**（必须，`worker_py/`） |
| Go Worker | **Go 1.22+**（必须，独立 module `worker/`） |
| Web | Vue3 + Vite；pnpm（可复议 npm） |
| Store | **SQLite**（写死） |
| Buffer/Cache | **Redis**（写死；两级队列） |
| Config | YAML |

## Global Constraints

1. 全链路 `trace_id`；头 `X-Trace-Id`。
2. 日志 JSON 必含：`trace_id`、`service`、`level`、`message`、`timestamp`。
3. 主仓 Go 服务不 import 本目录。
4. ingest **禁止**同步写 SQLite；写入仅 **Go Worker**；Python Worker 只做规范化入队。
5. 主业务 MySQL ≠ trace SQLite。
6. CORS 放开本地前端；密钥不进仓库。
7. 两级队列：`trace:ingest` / `trace:persist`（见 `AGENTS.md` §K）。

---

## Task 0：文档冻结评审

**前置**：无  
**预估**：0.5h  
**风险**：文档与实现分叉  

**Steps**

- [ ] 通读 `PRD.md` / `DESIGN.md` / `ARCHITECTURE.md` / 本 PLAN / `TODO.md`
- [ ] 确认默认决策：Python Worker + Go Worker + Redis 两级队列 + SQLite；API=FastAPI
- [ ] 确认与 `AGENTS.md` §D/§I/§J/**§K** 无冲突
- [ ] 目录存在 `backend/` `worker_py/` `worker/` `frontend/` `docs/`

**验收**

```bash
ls traceService/docs/{PRD,DESIGN,ARCHITECTURE,PLAN,TODO}.md
test -d traceService/worker_py && test -d traceService/worker
```

**Done 当**：评审勾选完成，决策表无 TBD。

---

## Task 1：后端骨架 FastAPI + 配置 YAML

**前置**：Task 0  
**预估**：1–2h  
**风险**：配置路径混乱  

**Files**：`backend/requirements.txt`、`backend/app/main.py`、`backend/app/config.py`、`backend/configs/default.yaml`

**Steps**

- [ ] 依赖：fastapi、uvicorn、pyyaml、pydantic、redis（async）等
- [ ] YAML：server、redis、sqlite.path、cors
- [ ] `GET /healthz` → 200
- [ ] README 指向启动命令

**验收**

```bash
cd traceService/backend && uvicorn app.main:app --port 8100
curl -s http://127.0.0.1:8100/healthz
```

**Done 当**：healthz 成功；改 yaml 重启生效（热更本 Task 不做）。

---

## Task 2：Redis 队列客户端 + ingest 只入队

**前置**：Task 1；本地 Redis  
**预估**：2h  
**风险**：Stream vs List API 差异  

**Steps**

- [ ] 封装 enqueue 到 **`trace:ingest`**（默认 Stream XADD；可配置 List LPUSH）
- [ ] `POST /api/v1/logs/ingest` 轻量校验 Pydantic → enqueue → `{accepted:N}`
- [ ] 队列超 `queue_soft_limit` → 50301
- [ ] **确认代码路径无 sqlite execute 写入**

**验收**

```bash
curl -s -X POST http://127.0.0.1:8100/api/v1/logs/ingest \
  -H 'Content-Type: application/json' \
  -d '{"logs":[{"trace_id":"11111111-1111-1111-1111-111111111111","service":"gateway","level":"INFO","message":"hi","timestamp":"2026-09-27T22:00:00+08:00"}]}'
# redis-cli 可见队列长度增加
```

**Done 当**：accepted≥1；SQLite 仍可无该行（Worker 未跑）。

---

## Task 3：Python Worker（消费 ingest → 规范化 → 入 persist）

**前置**：Task 2  
**预估**：2–4h  
**风险**：与 Go Worker 消息格式不一致  

**Files**：`worker_py/`（`main.py`、`consumer.py`、`normalize.py`、`producer.py`、`configs/default.yaml`、`requirements.txt`）

**Steps**

- [ ] 独立进程入口；配置：`trace:ingest` / `trace:persist`、batch
- [ ] 消费 `trace:ingest`（XREAD GROUP 或 BRPOP）
- [ ] 校验/规范化/enrich：level 大写、`msg`→`message`、补全可选字段
- [ ] 写入 `trace:persist`；**禁止**写 SQLite
- [ ] 日志带 `trace_id`；`service=trace-worker-py`
- [ ] graceful shutdown；幂等/有限重试（细节可复议）

**验收**

```bash
cd traceService/worker_py && python -m worker
# ingest 后：redis-cli 可见 trace:persist 增长；SQLite 仍可无行（Go Worker 未跑）
```

**Done 当**：ingest → Python Worker → `trace:persist` 打通；不写 SQLite。

---

## Task 4：初始化 Go Worker module + consumer + batch writer

**前置**：Task 3  
**预估**：4–6h  
**风险**：SQLite 锁、消息至少一次投递  

**Files**：`worker/go.mod`、`worker/cmd/worker/main.go`、`worker/internal/...`、`worker/configs/default.yaml`

**Steps**

- [ ] `go mod init`（module 路径自定，如 `aidramastic/traceService/worker`）
- [ ] 配置：redis **`trace:persist`**、sqlite path、batch_size、busy_timeout
- [ ] consumer：XREAD GROUP 或 BRPOP（消费 persist）
- [ ] writer：`PRAGMA journal_mode=WAL`；批量 INSERT；事务提交
- [ ] 写后按 `trace_id` DEL 查询缓存
- [ ] **graceful shutdown**（SIGINT/SIGTERM 刷完当前批）
- [ ] **背压/告警**：队列深度超阈值打 Error 日志（限流可后续）
- [ ] 日志带 `trace_id`；`service=trace-worker-go`

**验收**

```bash
cd traceService/worker && go run ./cmd/worker
# 再 ingest 后（需 Python Worker 已跑）：
sqlite3 traceService/backend/data/logs.db "SELECT trace_id,service,message FROM logs;"
```

**Done 当**：`trace:persist` 消息落入 SQLite；停 Go Worker 再启不丢（Redis 中残留可续）。

---

## Task 5：查询 API（缓存 → SQLite）

**前置**：Task 4  
**预估**：2h  
**风险**：缓存与 DB 不一致（写后 DEL 解决）  

**Steps**

- [ ] `GET /api/v1/logs?trace_id=`
- [ ] Redis GET → miss 则 SELECT ORDER BY timestamp ASC → SETEX
- [ ] 空列表非 null；缺参 400

**验收**

```bash
curl -s 'http://127.0.0.1:8100/api/v1/logs?trace_id=11111111-1111-1111-1111-111111111111'
```

**Done 当**：顺序正确；二次查询走缓存（可用日志/redis-cli 验证）。

---

## Task 6：可选 — mock 日志脚本

**前置**：Task 2（有双 Worker 更佳）  
**预估**：1h  

**Steps**

- [ ] `backend/scripts/gen_mock_logs.py` 多服务交错同一 trace_id
- [ ] 走 ingest API；打印 trace_id

**验收**：脚本退出码 0；query 可见多 service。

---

## Task 7：Vue3 前端时间线

**前置**：Task 5  
**预估**：2–3h  

**Steps**

- [ ] Vite Vue3；输入框 + 查询按钮 + 列表
- [ ] `VITE_API_BASE`；空态/错误态

**验收**：浏览器粘贴已知 trace_id 见时间线。

---

## Task 8：CORS / 本地联调 / 限流可选

**前置**：Task 7  
**预估**：1h  

**Steps**

- [ ] CORS origins 含 Vite 端口
- [ ] （可选）Redis 固定窗口限流
- [ ] 端口表写入 README

**验收**：前端 dev 跨域 query 成功。

---

## Task 9：README 启动验证（含双 Worker）

**前置**：Task 8  
**预估**：1h  

**Steps**

- [ ] 写清：Redis → API → Python Worker → Go Worker → 前端顺序
- [ ] curl ingest + query 示例
- [ ] `.gitignore` 含 `*.db`、`.venv`、worker bin
- [ ] 勾选已完成 Task

**Done 当**：陌生人 15 分钟内完成闭环。

---

## 验收总标准

- [ ] 不依赖 Jaeger/ELK
- [ ] ingest → `trace:ingest` → Python Worker → `trace:persist` → Go Worker → SQLite → query → Web
- [ ] 主路径不因 ingest 阻塞（约定 + 抽测）
- [ ] schema 与 AGENTS §D 一致；存储与 §J 一致；队列与 §K 一致
- [ ] 主仓无对本包代码依赖
- [ ] 目录含 `worker_py/` 与 `worker/`；技术栈表同时出现 Python Worker 与 Go Worker
