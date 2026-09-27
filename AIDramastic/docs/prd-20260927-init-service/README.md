# docs/prd-20260927-init-service/ — 文档索引

本目录是 **AIDramastic MVP 初始化** 的产品与工程文档集（2026-09-27）。

## 文档地图

| 文件 | 用途 |
|------|------|
| [`BACKGROUND.md`](BACKGROUND.md) | 纯背景：产品故事、动机、术语、里程碑 M0/M1/M2 |
| [`PRD.md`](PRD.md) | 产品需求：背景细目、服务拆分、协议、数据、验收 |
| [`DESIGN.md`](DESIGN.md) | 系统设计摘要：边界、序列、错误、热更、AI、可观测 |
| [`CODING_STANDARDS.md`](CODING_STANDARDS.md) | 工程规范：错误、分层、日志、测试、trace_id |
| [`TODO.md`](TODO.md) | MVP 脚手架落地 Checklist |

## 仓库其它入口

| 文件 | 用途 |
|------|------|
| [`../../AGENTS.md`](../../AGENTS.md) | Agent/人类工程宪法（含 §J 存储、**§K 队列与 Worker**） |
| [`../../README.md`](../../README.md) | 仓库总览 |
| [`../../traceService/README.md`](../../traceService/README.md) | 可观测子系统 |
| [`../../traceService/docs/`](../../traceService/docs/) | PRD / DESIGN / ARCHITECTURE / PLAN / TODO |

## 可观测默认架构（一句话）

漫剧：**Redis 队列 + Go Worker（ai-svc）**；trace：**FastAPI + Python Worker + Go Worker + Redis 两级队列 + SQLite**；业务侧异步上报、不阻塞主路径（见根 `AGENTS.md` §K）。
