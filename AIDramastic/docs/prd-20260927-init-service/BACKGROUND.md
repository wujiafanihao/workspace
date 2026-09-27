# AIDramastic 背景说明（BACKGROUND）

| 字段 | 内容 |
|------|------|
| 文档版本 | v0.3 |
| 日期 | 2026-09-27 |
| 状态 | 现行 |
| 关联 | 同目录 `PRD.md` / `DESIGN.md`；仓库根 `AGENTS.md` |

> 本文只讲「为什么做、给谁做、术语与里程碑」。需求条目与验收见 `PRD.md`；系统设计见 `DESIGN.md`。

---

## 1. 产品故事

创作者小陈想做一部短漫剧《月下》：先有文字剧本，再变成角色立绘、场景图、分镜，最后拼成可预览的短视频。今天若靠手工剪辑 + 零散 AI 网页工具，每换一家模型就要重新对接；多步失败时也不知道卡在「抽角色」还是「生视频」。

**AIDramastic** 要把这条链路收成一条可编排流水线：Web 写章 → LLM 抽资产 → 生图 → 拆分镜 → 视频生成。仓库当前阶段不追求成片质量，而追求**换模型不改业务、多服务能联调、出错能按 `trace_id` 查链**。

---

## 2. 市场与动机（一句话级）

| 动机 | 说明 |
|------|------|
| 模型迭代快 | seedance / keling / 各类 LLM·生图·视频 API 频繁换代，SDK 写死 = 持续返工 |
| 链路长 | 同一用户操作跨 gateway、user、drama、ai 多进程，没有统一追踪就无法联调 |
| 个人/小团队 | 付不起完整 APM 集群运维；需要本地可起的轻量可观测 |
| 与竞品差异（一句话） | 竞品多是「单厂商 Demo 工作台」；本项目强调 **Provider 可插拔 + 自研轻量 trace + Go 微服务边界**，先框架后真实 AI |

---

## 3. 目标用户（背景视角）

| 角色 | 诉求 |
|------|------|
| 个人创作者 | 一天内跑通「写章 → 出 stub 视频」；少运维 |
| 小团队（2–5 人） | 同一项目协作看资产/分镜；权限 MVP 仅本人资源隔离 |
| 开发者 / Agent | 按 AGENTS / PRD / TODO 落地脚手架；用 `trace_id` 排障 |
| 联调同学 | 起 docker MySQL/Redis + 各进程 + traceService，不必懂 Jaeger |

---

## 4. 术语表

| 术语 | 含义 |
|------|------|
| Project | 一部漫剧项目（如《月下》） |
| Chapter | 章节正文 |
| Character / Scene / Dialogue | 从正文抽取的结构化资产 |
| Storyboard / Shot | 分镜与镜头；视频任务挂在 Shot |
| Asset | 图片/视频等产物 URL 与元数据 |
| Job | ai-svc 异步任务（MySQL 状态 + Redis 队列；由 Go Worker 执行） |
| Provider / capacity / driver | YAML 注册的 AI 能力条目与实现驱动 |
| element_type | `llm` / `image` / `video` |
| gateway | HTTP BFF，对前端暴露 REST |
| trace_id | 全链路 UUID；HTTP 头 `X-Trace-Id` |
| span_id | 可选单步 ID |
| ingest | 业务侧把日志推到 traceService |
| traceService | 本仓独立子系统：FastAPI API + **Python Worker** + **Go Worker** + Vue3 + SQLite + Redis 两级队列 |

---

## 5. 里程碑愿景

| 里程碑 | 目标 | 非目标 |
|--------|------|--------|
| **M0（当前）** | 文档齐备；目录骨架；协议与规范写死；traceService 文档与计划齐套 | 真实 AI、生产部署 |
| **M1** | 四后端 + web 可本地联调；AI 全 mock；配置热更；按 `trace_id` 在 traceService 看跨服务时间线；ingest **不阻塞**主路径 | 付费、多租户、Jaeger |
| **M2** | 接入 1–2 家真实 driver；对象存储；可选 media-svc；trace 可演进 OpenTelemetry 导出 | 完整商业化运营台 |

---

## 6. 可观测背景（与硬性决策对齐）

主业务多进程后，「某次点抽取失败」必须能用一个 `trace_id` 拉齐 gateway → ai-svc → drama-svc 日志。MVP **不做** Jaeger/ELK 集群，自研 `traceService`。

**存储分层（写死）**：

| 系统 | 主库 | Redis |
|------|------|-------|
| 漫剧主系统（Go 微服务） | **MySQL**（用户/项目/章节/分镜/job…） | **队列**（`ai:jobs`）、JWT 黑名单、热点缓存；**不是**业务主库 |
| traceService | **SQLite** | ingest 缓冲 + 查询缓存 + 可选限流 |

traceService 进程形态（两级队列 + 双 Worker）：

- **持久化：SQLite**（写死；MVP 不改 MySQL）
- **两级队列 + 热点缓存：Redis**（`trace:ingest` / `trace:persist`）
- **API：FastAPI**；**Python Worker**（规范化）+ **Go Worker**（批量写 SQLite）
- 漫剧侧：**ai-svc = Redis `ai:jobs` + Go Worker**（见 `AGENTS.md` §K）
- 主业务上报：**短超时、失败可丢、异步 fire-and-forget**，绝不阻塞用户请求
- **禁止**主业务表落到 SQLite；**禁止**用进程内 goroutine 替代默认队列

细节见 `DESIGN.md`、`traceService/docs/ARCHITECTURE.md`、根 `AGENTS.md` §J / §K。

---

## 7. 文档索引

| 文档 | 用途 |
|------|------|
| `PRD.md` | 需求、服务拆分、验收 |
| `DESIGN.md` | 系统设计摘要 |
| `CODING_STANDARDS.md` | 工程规范 |
| `TODO.md` | 落地 Checklist |
| `README.md` | 本目录索引 |
| `../../AGENTS.md` | 工程宪法 |
| `../../traceService/docs/` | 可观测全套文档 |
