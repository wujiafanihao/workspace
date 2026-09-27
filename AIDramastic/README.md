# AIDramastic（AI 漫剧）

> 用户写剧本/章节 → LLM 抽角色·场景·台词 → 生图 → 拆分镜 → 视频生成，串成可编排的 **AI 漫剧流水线**。

本仓库当前目标是搭好 **可编译、可联调、可扩展** 的 MVP 微服务框架（业务与真实 AI 一律 mock/stub），规范与可观测先行。

---

## 仓库结构

```
AIDramastic/
├── app/                      # Go 微服务实现
│   ├── application/          # gateway / user-svc / drama-svc / ai-svc
│   └── shared/               # config 热更、logger、errors、jwt、mysql、redis…
├── protocol/                 # proto 源与生成代码
│   ├── application/          # user / drama / ai
│   └── shared/               # 公共消息、错误约定
├── web/                      # 主业务前端（Vue3）
├── traceService/             # 独立可观测：按 trace_id 查跨服务日志（Python FastAPI + Vue3）
├── configs/                  # 各服务 YAML 示例（落地后）
├── docs/
│   └── prd-20260927-init-service/
│       ├── PRD.md
│       ├── CODING_STANDARDS.md
│       └── TODO.md
├── AGENTS.md                 # AI Agent / 人类工程宪法（编码权威入口）
└── README.md
```

---

## 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Go、gRPC、HTTP BFF（gateway）、MySQL、Redis |
| AI | Provider Registry；YAML `element_type` / `capacity` / `driver` 可插拔（MVP：`mock`） |
| 配置 | YAML + 热更新；密钥用 env 名引用 |
| 主前端 | Vue3 + Vue Router + Pinia + Axios（pnpm） |
| 可观测 | 自研 `traceService`（FastAPI + Vue3 + SQLite）；全链路 `trace_id` |

---

## 文档索引

| 文档 | 说明 |
|------|------|
| [`docs/prd-20260927-init-service/PRD.md`](docs/prd-20260927-init-service/PRD.md) | 产品背景、服务拆分、协议与数据模型 |
| [`docs/prd-20260927-init-service/CODING_STANDARDS.md`](docs/prd-20260927-init-service/CODING_STANDARDS.md) | 错误处理、分层、测试等工程细节 |
| [`docs/prd-20260927-init-service/TODO.md`](docs/prd-20260927-init-service/TODO.md) | MVP 脚手架落地 Checklist |
| [`AGENTS.md`](AGENTS.md) | **编码与工程宪法**（Agent 必读；与 CODING_STANDARDS 冲突时产品级约定以本文件优先说明） |
| [`traceService/README.md`](traceService/README.md) | 轻量 Trace / 日志查询子系统 |
| [`traceService/docs/PLAN.md`](traceService/docs/PLAN.md) | traceService 开发计划 |

---

## 本地启动（MVP）

> 脚手架尚未齐备，详见 [`TODO.md`](docs/prd-20260927-init-service/TODO.md)。以下为**预期**启动顺序，实现后按实际命令更新本段。

**前置（规划）**：Go 1.22+、Node 20+ / pnpm、Docker（可选）、Python 3.11+（仅 traceService）。

**预期顺序**：

1. `docker compose up -d`（MySQL + Redis，若使用）
2. 复制 `.env.example` → `.env`，填入 `MYSQL_DSN` / `REDIS_ADDR` / `JWT_SECRET` 等
3. `make gen` 生成 protobuf
4. 启动后端（顺序可并行，建议先下游）：`user-svc` → `drama-svc` → `ai-svc` → `gateway`
5. （可选并行）启动 `traceService` 后端与其 Web，用于按 `trace_id` 查日志
6. `cd web && pnpm install && pnpm dev`

默认端口与确切二进制命令以 configs / Makefile 落地为准。

---

## 可观测

- **所有** HTTP / gRPC 请求必须传播 `trace_id`（客户端可传 `X-Trace-Id`；缺失则由 gateway/入口生成 UUID）。
- 结构化日志每条带 `trace_id`、`service`、`level`、`msg`、时间；推荐 JSON 一行一条。
- 查日志：打开 **traceService** Web，输入 `trace_id`，查看跨服务时间线。
- 约定与上报方式见根目录 [`AGENTS.md`](AGENTS.md) 与 [`traceService/README.md`](traceService/README.md)。**禁止**依赖 Jaeger/ELK 才能本地开发。

---

## 贡献 / 规范

以仓库根 [`AGENTS.md`](AGENTS.md) 为准；细节对齐 [`CODING_STANDARDS.md`](docs/prd-20260927-init-service/CODING_STANDARDS.md)。提交前确认：无真实密钥、无手改 `*.pb.go`、业务错误不 panic。
