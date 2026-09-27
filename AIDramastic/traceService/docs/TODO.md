# traceService 执行 TODO（细 Checklist）

> **背景摘要**：落实轻量 trace——FastAPI 入队、**Python Worker** 规范化、**Go Worker** 写 SQLite、Redis 两级队列；主业务 MySQL 不掺和。依据 `PRD.md` / `PLAN.md` / `AGENTS.md` §J / **§K**。

---

## Day 0 — 文档与环境

- [ ] 读完 PRD / DESIGN / ARCHITECTURE / PLAN
- [ ] 确认本机：Python 3.11+、Go 1.22+、Node20/pnpm、Redis
- [ ] Redis 可连通：`redis-cli ping`
- [ ] 目录：`backend/` `worker_py/` `worker/` `frontend/` `docs/`
- [ ] Task 0 文档冻结勾选

---

## 后端 FastAPI

- [ ] `requirements.txt` + venv
- [ ] `app/config.py` 读 YAML
- [ ] `app/main.py` 挂载路由 + CORS
- [ ] `GET /healthz`
- [ ] Pydantic：`LogIn` / `IngestBody`
- [ ] Redis 连接（addr 来自 env）
- [ ] `enqueue`：写入 **`trace:ingest`**（Stream 或 List）
- [ ] `POST /api/v1/logs/ingest` 只入 `trace:ingest`
- [ ] 队列软上限 → 503
- [ ] 单测或手工：非法 body → 400
- [ ] 确认 ingest 路径无写 SQLite

---

## DB（SQLite 只读侧 + Worker 写侧）

- [ ] 约定 `sqlite.path` 与 Worker 一致
- [ ] API 只读打开；`PRAGMA` 查询侧可省略 WAL（Writer 侧必须 WAL）
- [ ] DDL 与 DESIGN 一致（id/trace_id/span_id/service/level/message/timestamp/fields_json/created_at）
- [ ] 索引 `trace_id`、`(trace_id,timestamp)`

---

## Python Worker

- [ ] `worker_py/` 入口与依赖
- [ ] 配置：`trace:ingest` / `trace:persist`
- [ ] 消费 ingest 循环
- [ ] normalize / enrich
- [ ] 生产 persist；**确认不写 SQLite**
- [ ] 日志带 `trace_id`；graceful shutdown
- [ ] 有限重试 / 幂等约定

---

## Go Worker

- [ ] `worker/go.mod` 初始化
- [ ] 配置加载（yaml/env）；消费 **`trace:persist`**
- [ ] consumer 循环
- [ ] batch buffer + flush 定时/满批
- [ ] SQLite writer：WAL、busy_timeout、事务批量
- [ ] 写后缓存 DEL `trace:{id}`
- [ ] graceful shutdown
- [ ] 队列深度日志/告警
- [ ] `go build` / `go run` 验证
- [ ] Worker `.gitignore` 输出二进制

---

## 查询 API

- [ ] cache get
- [ ] miss → SQL ORDER BY timestamp ASC
- [ ] backfill SETEX ttl=60
- [ ] 空数组；缺参 400
- [ ] curl 验收两条用例（有数据/无数据）

---

## 前端

- [ ] Vite Vue3 脚手架
- [ ] 输入框 + 按钮
- [ ] 时间线：时间、service、level、message
- [ ] 空态、错误态
- [ ] `VITE_API_BASE`

---

## 联调

- [ ] 启 Redis → API → Python Worker → Go Worker → Web
- [ ] mock 脚本推多服务日志
- [ ] Web 见时间线
- [ ] 停 Go Worker：ingest 仍 200；启后数据可见
- [ ] 停 Python Worker：`trace:ingest` 堆积；启后流入 persist
- [ ] 停 Redis：ingest 失败；主业务（若在跑）仍正常（上报丢弃）
- [ ] 粗压：连续 curl ingest，观察 API 延迟与队列深度

---

## 文档勾选

- [ ] 更新 `traceService/README.md` 启动步骤（含 **双 Worker**）
- [ ] PLAN 中完成的 Task 打勾
- [ ] 与主仓 AGENTS 对齐检查表（DESIGN §10）全部勾选
- [ ] 确认未把 trace 主库写成 MySQL；未把业务表写到 SQLite

---

## 与主仓约定对齐

- [ ] 字段名 `trace_id` / 头 `X-Trace-Id`
- [ ] 业务侧异步上报说明已写在主仓 DESIGN/CODING_STANDARDS/TODO O 节
- [ ] 错误体风格 `{code,message,data}`
- [ ] 端口不与 gateway 冲突（默认 8100 / 5174）
