# AIDramastic MVP 脚手架落地 Checklist

> **背景摘要**：本清单落地「可编译、可联调」的 MVP 框架（mock AI）。主业务：**Go + MySQL + Redis（队列/缓存）+ Vue3**；ai-svc = **API + Go Worker**。可观测：独立 `traceService`（**FastAPI + Python Worker + Go Worker + Redis + SQLite**），业务侧异步上报、不阻塞。详见 [`BACKGROUND.md`](BACKGROUND.md) / [`PRD.md`](PRD.md) / [`DESIGN.md`](DESIGN.md)；宪法 [`AGENTS.md`](../../AGENTS.md)（含 **§K 队列与 Worker**）。

> 按顺序执行；全部勾选即 MVP 框架可本地联调。依据同目录 `PRD.md` / `CODING_STANDARDS.md`。

---

## A. 仓库与规范文档确认

- [ ] 确认本目录文档齐备：`BACKGROUND.md`、`PRD.md`、`DESIGN.md`、`CODING_STANDARDS.md`、`TODO.md`、`README.md`
- [ ] 确认仓库骨架目录存在：`app/application`、`app/shared`、`protocol/application`、`protocol/shared`、`web/`、`docs/`、`traceService/`
- [ ] 确认根目录 `AGENTS.md`、`README.md`、`.gitignore` 已填写
- [ ] 确认 Go module 路径（`go.mod`）并在文档/Makefile 中统一引用
- [ ] 约定生成代码输出目录并写入 Makefile 注释（与 CODING_STANDARDS §6 一致）
- [ ] 主分支保护策略口头确认（默认 `main`；可复议）

---

## B. protocol 初版 proto + buf/protoc 脚本

- [ ] 新增 `protocol/shared` 公共 proto：`PageRequest` / `PageResponse` / 空消息或 ErrorDetail 注释
- [ ] 新增 `protocol/application/user/v1/user.proto`：Register/Login/Logout/GetProfile/UpdateProfile/UploadAvatar
- [ ] 新增 `protocol/application/drama/v1/drama.proto`：Project/Chapter/Character/Scene/Storyboard 相关 RPC 清单（见 PRD）
- [ ] 新增 `protocol/application/ai/v1/ai.proto`：Extract/Generate*/Split/GetJob/ListJobs
- [ ] 添加 `buf.yaml` / `buf.gen.yaml` 或 `scripts/gen.sh` + 根目录 `make gen`
- [ ] 执行一次 `make gen`，确认生成 Go 代码可编译（空实现即可）
- [ ] 在 `protocol/README.md`（若无可跳过）或 Makefile 注释写明「禁止手改 pb.go」

---

## C. app/shared：基础设施

- [ ] `config`：`Load(path)` + `Watch`（fsnotify 或定时），快照用 `atomic.Value`；失败保留旧配置
- [ ] `errors`：`BizError{Code,Message}` + 与 gRPC codes 映射函数 + 单测
- [ ] `logger`：统一 slog/zap 封装，注入 ctx 字段（`trace_id` 必填；可兼容 request_id）
- [ ] `mysql`：基于 DSN env 的连接池封装，方法一律带 `context.Context`
- [ ] `redis`：客户端封装；提供 JWT 黑名单 SetNX/Exists 与通用 Get/Set 带 ctx
- [ ] `jwt`：签发 / 解析 HS256；claims 含 `sub`、`jti`、`exp`
- [ ] `grpc/middleware`：recovery（转 Internal，不 panic 出进程）、logging、可选 auth 透传 metadata
- [ ] 单测：config 热更失败保留旧值；错误码映射表

---

## D. user-svc 骨架 + mock 登录 JWT

- [ ] `cmd/server/main.go`：加载 yaml、初始化 mysql/redis/logger、注册 gRPC
- [ ] `internal/repo`：users 表 CRUD（按 `scripts/sql` 或 migrate）
- [ ] `internal/service`：Register（bcrypt）、Login（发 JWT）、Logout（Redis 黑名单）、Profile 读写
- [ ] `internal/handler`：实现 user.v1 全部 RPC，错误走 BizError 映射
- [ ] 本地手动验证：注册 → 登录拿 token → GetProfile → Logout → 旧 token 拒绝
- [ ] 服务监听地址写入 `configs/user-svc.yaml`（见 H）

---

## E. drama-svc 骨架 + CRUD stub

- [ ] `cmd/server/main.go` + gRPC 注册 drama.v1
- [ ] 迁移/SQL：projects、chapters、characters、scenes、dialogues、storyboards、shots、assets 表
- [ ] repo + service：Create/List/Get Project；Chapter CRUD；ListCharacters/Scenes/Storyboards；GetStoryboard
- [ ] 所有写操作校验 `user_id`（从 metadata 取）归属，防越权
- [ ] Chapter status 字段按 PRD 枚举落库（draft 起）
- [ ] handler 层完成 proto ↔ model 转换；空列表返回空 slice 非 null

---

## F. ai-svc 骨架 + Provider Registry + mock drivers + Redis 队列

- [ ] 定义 `LLMProvider` / `ImageProvider` / `VideoProvider` 接口与请求/响应结构体
- [ ] 实现 `mock` driver（llm/image/video）：短延迟 + 固定 stub JSON/`asset_url`
- [ ] Registry：`(element_type, capacity)` 索引；yaml 加载；`enabled=false` 跳过
- [ ] 热更：watch yaml 重建 Registry，失败保留旧 Registry + Error 日志
- [ ] `ai_jobs` 表 + repo
- [ ] **API 进程** `cmd/server`：RPC 创建 job（MySQL pending）→ **XADD Redis Stream `ai:jobs`**（带 `job_id`/`trace_id`）→ 立即返回；GetJob/ListJobs 只查库
- [ ] **禁止** handler/service 同步调 Provider（mock 也不例外）
- [ ] 实现 ExtractChapterAssets / GenerateCharacterImage / GenerateSceneImage / SplitStoryboards / GenerateShotVideo / GetJob / ListJobs（API 侧）
- [ ] Job 锁 key 约定落地（`ai:job:lock:{job_id}`）
- [ ] 单测：Registry 查找与禁用；mock driver 返回非空结果

---

## F2. ai-worker（Go Worker 进程，强制）

- [ ] `app/application/ai-svc/cmd/worker/main.go`：独立进程，加载同一套 yaml / Registry
- [ ] 消费 Redis Stream `ai:jobs`（消费者组可复议）；解析 `job_id`/`trace_id`
- [ ] 执行 Provider → 回写 MySQL `running`→`succeeded`/`failed` + `result_json`
- [ ] 幂等（按 job_id）；有限重试；失败进死信约定（字段或独立 stream）
- [ ] 日志带 `trace_id` + `job_id`；`service=ai-worker`
- [ ] graceful shutdown；与 API 联调：创建 job 后 Worker 未启则 pending，启后追上
- [ ] **确认无「进程内 goroutine 当默认 worker」代码路径**

---

## G. gateway HTTP + JWT + 转发

- [ ] HTTP Server（默认标准库 net/http 或 chi/gin，选定一种写进代码；默认 **chi**，可复议）
- [ ] 中间件：CORS（开发）、`X-Trace-Id` / `trace_id` 生成与透传、JWT 校验 + Redis 黑名单、统一错误体 `{code,message,data}`
- [ ] 路由对接：`/api/v1/auth/*`、`/api/v1/users/me`、`/api/v1/projects/**`、`/api/v1/ai/**`
- [ ] gRPC 客户端拨号 user/drama/ai；将 `x-user-id` 与 authorization 写入 metadata
- [ ] 编排示例接口（可选）：「抽取并写回角色」串行调 ai 再调 drama——若不做，文档注明由前端串行
- [ ] 健康检查：`GET /healthz` 返回 200

---

## H. configs 示例 yaml

- [ ] 创建仓库根目录 `configs/`（若不存在）
- [ ] `configs/user-svc.yaml`：grpc_addr、mysql/redis/jwt 的 env 引用、log
- [ ] `configs/drama-svc.yaml`：同上（无 jwt 签发也可要 secret 校验，按实现）
- [ ] `configs/ai-svc.yaml`：含完整 `ai.providers` mock 三段（llm/image/video）
- [ ] `configs/gateway.yaml`：http_addr、jwt、redis、downstream 三个 grpc 地址
- [ ] 示例中密钥均为 `*_env` 占位；附 `.env.example`（`MYSQL_DSN`、`REDIS_ADDR`、`JWT_SECRET`）
- [ ] 确认示例 yaml 不包含真实密码

---

## I. web Vue3 脚手架 + 路由 + API 封装 + 空页面

- [ ] 在 `web/` 初始化 Vue3（Vite）+ Vue Router + Pinia + Axios；包管理默认 pnpm
- [ ] 封装 `src/api/http.ts`：baseURL、Bearer token、统一错误 toast/日志
- [ ] 封装 auth/project/chapter/ai API 函数（与 gateway 路径对齐）
- [ ] 路由与空页面：登录、个人中心、项目列表、章节编辑、资产列表、分镜列表
- [ ] 登录成功存储 token；路由守卫未登录跳转 `/login`
- [ ] 环境变量：`VITE_API_BASE` 指向 gateway
- [ ] `pnpm dev` 可打开页面并完成一次登录联调（后端就绪后）

---

## J. docker-compose（mysql/redis）可选

- [ ] 根目录 `docker-compose.yml`：MySQL 8 + Redis 7，端口与 `.env.example` 一致
- [ ] MySQL 初始化挂载 `scripts/sql/001_init.sql`（或空库 + migrate）
- [ ] 文档说明：`docker compose up -d` 后等待 healthy 再启服务
- [ ] 数据目录用 named volume，避免误提交数据文件

---

## K. README 启动说明

- [ ] 根 `README.md` 补充（若当前为空壳则填写）：项目简介一句话 + 链接到 `docs/prd-20260927-init-service/`
- [ ] 写明前置：Go / Node / Docker 版本下限
- [ ] 启动步骤：compose → env → make gen → 四 API 服务 + **ai-worker** → web dev（trace 另起 API+双 Worker）
- [ ] 写明默认端口表：gateway HTTP、各 svc gRPC、MySQL、Redis、Vite
- [ ] 写明「AI 均为 mock；换厂商只改 yaml + driver」
- [ ] 不在 README 粘贴真实密钥

---

## O. 可观测 / traceService（可并行 · 两级队列 + 双 Worker）

- [ ] 阅读根目录 `AGENTS.md` §D / §I / **§J** / **§K** 与 `traceService/README.md`、`traceService/docs/PRD.md`
- [ ] 确认存储：主业务 MySQL；trace SQLite；Redis 两边都有队列
- [ ] 确认目录：`backend/` + `worker_py/` + `worker/` + `frontend/`
- [ ] 按 `traceService/docs/PLAN.md`：FastAPI 骨架 + YAML + `/healthz`
- [ ] Redis：`trace:ingest` / `trace:persist` + 查询缓存 key 约定
- [ ] `POST /api/v1/logs/ingest`：校验后**只写 `trace:ingest`**，立即返回（不写 SQLite）
- [ ] **Python Worker**（`traceService/worker_py`）：消费 `trace:ingest` → 规范化/enrich → 入 `trace:persist`
- [ ] **Go Worker**（`traceService/worker`）：消费 `trace:persist` → 批量写 SQLite（WAL）→ 维护 trace 缓存
- [ ] `GET /api/v1/logs?trace_id=`：Redis 缓存 → SQLite → 回填；时间升序
- [ ] （可选）`backend/scripts/gen_mock_logs.py` 模拟跨服务日志
- [ ] Vue3 查询 Web：输入 `trace_id` + 时间线列表
- [ ] CORS / 本地联调；更新 `traceService/README.md`（含 **两个** Worker 启动）
- [ ] gateway/各 svc：`X-Trace-Id` 透传；**异步** ingest（短超时、失败可丢）
- [ ] 联调验收：完整请求 → 同一 `trace_id` 在 Web 见跨服务时间线；压测确认主路径不被 ingest 拖慢

---

## 完成定义（再勾一次）

- [ ] 四后端 API + **ai-worker** + web 本地可起
- [ ] 注册登录 → 建项目 → 写章节 → 触发 Extract（入队）→ Worker 跑 mock → GetJob succeeded
- [ ] 修改 `ai-svc.yaml` providers 后热更生效（或失败保留旧配置有日志）
- [ ] 无真实密钥入库；无手改 pb.go
- [ ] 任意请求带 `trace_id`；traceService 可按该 id 查到日志（O 节闭环）
