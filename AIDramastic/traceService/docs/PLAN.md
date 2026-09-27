# traceService 开发计划

> 风格：Goal / Architecture / Tech / Constraints + checkbox Tasks。  
> 本次以 **plan 定开发路径** 为主；实现按 Task 顺序勾选推进。

---

## Goal

提供可独立运行的轻量日志检索服务：业务服务（或模拟脚本）上报 JSON 日志后，用户在 Web 输入 `trace_id` 即可看到跨服务时间线。不依赖 Jaeger/ELK。

## Architecture（摘要）

```
业务服务 / mock 脚本
    │  POST /api/v1/logs/ingest  （默认）
    │  或写约定目录由采集器尾随（可选）
    ▼
traceService backend (FastAPI)
    │  校验 schema → 写入 SQLite
    ▼
SQLite (logs 表)
    │  GET /api/v1/logs?trace_id=
    ▼
traceService frontend (Vue3)  → 时间线 UI
```

详见同目录 `ARCHITECTURE.md`。

## Tech Stack

- Backend: Python 3.11+、FastAPI、uvicorn、Pydantic、SQLite（SQLAlchemy 或 aiosqlite，实现时选定）
- Frontend: Vue3 + Vite；包管理 pnpm（可复议 npm）
- Config: YAML（如 `backend/configs/default.yaml`）
- 默认上报：HTTP ingest

## Global Constraints（与 AGENTS.md 一致）

1. 全链路 `trace_id`（UUID）；HTTP 头 `X-Trace-Id`。
2. 日志 JSON 至少含：`trace_id`、`service`、`level`、`message`、`timestamp`。
3. 主仓 Go 服务不 import 本目录；只走协议。
4. MVP 不做完整 APM；SQLite 默认可复议 PostgreSQL。
5. CORS 放开本地前端源；密钥不进仓库。

---

## Task 1：后端骨架 FastAPI + 配置 YAML

**Files（预计）**

- `backend/requirements.txt`
- `backend/app/main.py`
- `backend/app/config.py`
- `backend/configs/default.yaml`
- `backend/app/__init__.py`

**Steps**

- [ ] 初始化包结构与依赖列表（fastapi、uvicorn、pyyaml、pydantic-settings 等）
- [ ] 从 YAML 加载 `server.host/port`、`db.path`、`cors.origins`
- [ ] `GET /healthz` 返回 200 JSON
- [ ] README 中启动命令可指向本骨架

**Done 当**

- 本地 `uvicorn` 能起；访问 `/healthz` 成功；改 yaml 重启后配置生效（热更本 Task 不做）。

---

## Task 2：SQLite 模型（logs 表）+ ingest API

**Files（预计）**

- `backend/app/db.py`
- `backend/app/models/log.py`
- `backend/app/api/ingest.py`
- `backend/app/schemas/log.py`

**Steps**

- [ ] 建表 `logs`：`id`, `trace_id`, `span_id`, `service`, `level`, `message`, `timestamp`, `fields_json`, `created_at`
- [ ] 索引：`trace_id`、`(trace_id, timestamp)`
- [ ] `POST /api/v1/logs/ingest`：接受单条对象或 `{ "logs": [...] }`
- [ ] Pydantic 校验必填字段；非法请求 400
- [ ] 写入成功返回 `{ "code": 0, "message": "ok", "data": { "accepted": N } }`（风格可与主仓错误体对齐）

**Done 当**

- curl 推入 2 条不同 `trace_id` 的日志，库中可见对应行。

---

## Task 3：按 trace_id 查询 API（时间排序）

**Files（预计）**

- `backend/app/api/query.py`

**Steps**

- [ ] `GET /api/v1/logs?trace_id=<uuid>`
- [ ] 缺参 400；无数据返回空列表非 null
- [ ] 结果按 `timestamp` **升序**
- [ ] 响应体含完整日志字段，便于前端渲染

**Done 当**

- 对 Task 2 写入的 `trace_id` 查询，顺序与时间戳一致。

---

## Task 4：可选 — 模拟日志生成脚本

**Files（预计）**

- `backend/scripts/gen_mock_logs.py`

**Steps**

- [ ] 脚本生成同一 `trace_id` 下多服务（gateway / user-svc / drama-svc / ai-svc）交错日志
- [ ] 通过 ingest API 推送（或直写 DB，优先走 API）
- [ ] 打印所用 `trace_id` 便于 Web 粘贴

**Done 当**

- 跑脚本后 Web/查询 API 能看到多服务时间线。

---

## Task 5：Vue3 前端 — 输入框 + 时间线列表

**Files（预计）**

- `frontend/` Vite Vue3 脚手架
- `frontend/src/App.vue`（或 views）
- `frontend/src/api/logs.ts`

**Steps**

- [ ] 页面：`trace_id` 输入框 + 查询按钮
- [ ] 调用 query API，列表展示：时间、service、level、message
- [ ] 空态 / 错误态提示
- [ ] 环境变量 `VITE_API_BASE` 指向后端

**Done 当**

- 浏览器输入已知 `trace_id` 可见时间线；错误 `trace_id` 显示空列表。

---

## Task 6：CORS / 本地联调

**Files（预计）**

- `backend/app/main.py`（CORS middleware）
- `backend/configs/default.yaml`（origins）

**Steps**

- [ ] 配置允许本地 Vite origin（如 `http://127.0.0.1:5174`）
- [ ] 前端跨域查询与 ingest（若从浏览器测）无 CORS 报错
- [ ] 在 PLAN/README 写明默认端口表

**Done 当**

- 前端 dev server 调后端 query 成功。

---

## Task 7：README 启动验证步骤

**Files**

- `traceService/README.md`（更新「本地启动」为可执行步骤）

**Steps**

- [ ] 写清依赖安装、启后端、启前端、curl ingest 示例、Web 验证路径
- [ ] 注明 SQLite 文件路径与 `.gitignore` 已忽略 `*.db`
- [ ] 勾选本 PLAN 已完成的 Task

**Done 当**

- 陌生人按 README 可在 15 分钟内完成：ingest → 查询 → Web 看到时间线。

---

## 验收总标准

- [ ] 不依赖 Jaeger/ELK
- [ ] ingest + query + Web 闭环
- [ ] JSON schema 与 AGENTS.md §D 一致
- [ ] 主仓无对本包的代码依赖
