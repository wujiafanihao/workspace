# AIDramastic（AI 漫剧）MVP 初始化 PRD

| 字段 | 内容 |
|------|------|
| 项目名 | AIDramastic（AI 漫剧） |
| 文档版本 | v0.1 |
| 日期 | 2026-09-27 |
| 目标 | 快速搭可运行的 MVP 框架（mock/stub），不交付真实 AI/业务能力 |
| 技术栈 | Go gRPC 微服务 + Vue3 前端 + MySQL + Redis |
| 配置 | YAML + 热更新；AI 提供商可插拔 |

---

## 1. 背景与目标

### 1.1 背景

#### 1.1.1 产品愿景

**AIDramastic（AI 漫剧）** 面向创作者与团队，把「写剧本 → 出漫剧」做成一条可编排的 AI 流水线：

1. 用户在 Web 上创建项目、撰写章节剧本；
2. LLM 从正文中抽取角色、场景、台词等结构化资产；
3. 生图模型为角色/场景生成立绘或场景图；
4. 再按章节拆分镜（Storyboard / Shot）；
5. 视频模型按分镜生成短片，最终串成可预览的 AI 漫剧。

本仓库要支撑的不是单次 Demo，而是**可持续换模型、可拆服务、可联调**的产品底座。

#### 1.1.2 问题与动机

漫剧生产链路长、外部 AI 厂商多（如 seedance、keling、各类 LLM/生图/视频 API），且后期**模型与供应商会频繁更换**。若把厂商 SDK 写死在业务里，每次换模型都要大改。

因此 MVP 起就定下：

- **微服务边界**：用户、内容（drama）、AI 任务、HTTP 网关分进程，便于独立扩容与联调；
- **AI 可插拔**：按 YAML 的 `element_type` / `capacity` / `driver` 注册 Provider，业务只调接口；
- **配置热更**：换 mock 或增厂商条目尽量不重启、不改业务代码。

#### 1.1.3 当前仓库状态

仓库已有**空壳骨架**（无业务实现），目录大致为：

- `app/application`、`app/shared`
- `protocol/application`、`protocol/shared`
- `web/`
- `docs/`
- `traceService/`（独立可观测子系统占位）

根目录 `README.md` / `AGENTS.md` / `.gitignore` 等亦待本次补齐。

#### 1.1.4 本阶段定位

本阶段目标是 **MVP 框架优先**：可编译、可联调、可扩展；业务与真实 AI 调用一律 **mock/stub**。规范（错误处理、分层、`trace_id`）、配置热更与可观测约定先行，真实厂商接入与完整产品能力放到后续迭代。

### 1.2 成功标准（Done Definition）

1. 本地用 docker-compose（或本机）起 MySQL + Redis 后，4 个后端进程 + 1 个前端可启动。
2. 用户可：注册/登录 → 建项目 → 写章节 → 触发 AI 任务（mock 立即/短延迟成功）→ 查看资产/分镜列表。
3. AI Provider 通过 YAML 按 `(element_type, capacity)` 注册；换 mock driver / 增厂商条目不改业务代码。
4. 配置 YAML 热更：改 AI providers / DSN 等后进程无需重启（失败保留旧配置）。
5. HTTP 统一错误体 `{code,message,data}`；gRPC 用 status + 业务错误 detail。
6. 任意请求携带 `trace_id`；可用 **traceService** Web 按 `trace_id` 查到对应跨服务日志时间线。

### 1.3 非目标（Out of Scope）

- 真实大模型 / 生图 / 视频厂商调用
- 支付、订阅
- 细粒度 RBAC（MVP：登录即本人资源；跨用户隔离用 `user_id` 过滤即可）
- 对象存储真实上传（本地路径或假 URL）
- K8s / 生产级部署；不做完整 APM/Jaeger 集群——MVP 用自研轻量 **traceService**（日志按 `trace_id` 检索）即可
- media 独立服务（后期再拆；MVP 媒体 URL/任务状态放在 `ai-svc` + `drama-svc`）

---

## 2. 服务拆分（默认方案）

**一句话摘要**：MVP 跑 **gateway（HTTP BFF）+ user-svc + drama-svc + ai-svc + web（Vue3）** 共 5 个进程；按「可独立扩容 / 可独立换厂商」划边界，不过细拆以免拖慢脚手架。

### 2.1 为何不拆更碎

- MVP 目标是**框架可跑**，不是微服务教科书演示。
- 媒体、权限、通知等独立服务会增加 proto、部署、联调成本，收益在 stub 阶段接近零。
- 边界原则（可复议）：
  - **可独立扩容**：AI 任务重、用户轻 → `ai-svc` 单独进程。
  - **可独立换厂商**：所有外部 AI 进 `ai-svc` Provider Registry。
  - **读写内容元数据**：项目/章节/角色/场景/分镜落在 `drama-svc`，不直接调外部 AI。

### 2.2 进程职责

#### 2.2.1 gateway（HTTP BFF）

- 对 Vue3 暴露 REST/JSON（默认：手写 HTTP handler 调下游 gRPC；可复议改为 grpc-gateway）。
- JWT 校验（读 Authorization Bearer）、统一错误体、将用户身份写入 gRPC metadata（如 `x-user-id`、`authorization`）。
- 聚合调用：user / drama / ai 三个下游。
- **不做业务落库**。

#### 2.2.2 user-svc

- 注册 / 登录 / 登出、JWT 签发与黑名单（Redis）、头像 URL、个人信息 CRUD。
- 密码：bcrypt（或 argon2，默认 bcrypt，可复议）。
- Logout：JWT jti 写入 Redis 黑名单，TTL = token 剩余有效期。

#### 2.2.3 drama-svc（内容域）

- Project、Chapter、Storyboard/Shot、Character、Scene、Dialogue 的元数据 CRUD 与简单状态机。
- **不直接调外部 AI**；由 gateway 或前端编排：先调 `ai-svc` 拿 job/结果，再回写 drama（或 ai-svc 回调/写回，MVP 默认由 **gateway/前端串行调用**，可复议）。
- 默认编排决策（可复议）：**前端/gateway 串行调用 ai → 成功后调 drama 更新状态**；ai-svc 不反向依赖 drama，降低环依赖。

#### 2.2.4 ai-svc

- Stub 能力：LLM 抽取角色/场景/台词、生图（角色属性图/场景图）、分镜拆分、视频生成。
- **Provider Registry**：按 yaml 的 `element_type` + `capacity` 加载；业务只调接口。
- 异步 Job：`pending/running/succeeded/failed`；MVP mock 可立即或短延迟（如 100–500ms）成功，返回 stub `asset_url`。

#### 2.2.5 web（Vue3）

- 页面：登录、个人中心、项目列表、章节编辑、资产/分镜列表。
- MVP：空页面 + 路由 + API client 即可，样式可用最简布局。

### 2.3 可选后期

- `media-svc`：真实对象存储、转码、CDN。
- 消息队列驱动 AI 任务（MVP 用进程内 goroutine + DB job 表即可）。

---

## 3. 目录约定（与现有骨架对齐）

```
AIDramastic/
  protocol/
    shared/                 # 公共错误码、common.proto、分页等
    application/
      user/v1/
      drama/v1/
      ai/v1/
  app/
    shared/                 # config热更、logger、errors、jwt、mysql、redis、grpc middleware
    application/
      gateway/
      user-svc/
      drama-svc/
      ai-svc/
  web/                      # Vue3（主业务前端）
  traceService/             # 独立可观测子系统：Python FastAPI + Vue3；不阻塞主业务服务
  configs/                  # 各服务 yaml 示例（TODO 中创建）
  docs/
    prd-20260927-init-service/
```

单服务内部建议分层（与 CODING_STANDARDS 一致）：

```
app/application/<svc>/
  cmd/server/main.go
  internal/
    handler/          # gRPC / HTTP 入口
    service/          # 业务编排
    repo/             # MySQL/Redis
    adapter/          # 外部依赖（ai provider 实现放这里）
  configs/            # 可选：服务内示例；全局示例优先放仓库根 configs/
```

---

## 4. Protocol 定义原则

### 4.1 约定

- 一律 **proto3**，包名：`aidramastic.<domain>.v1`（如 `aidramastic.user.v1`）。
- RPC 命名：**VerbNoun**（`CreateProject`、`ListChapters`）。
- 业务错误：gRPC `status` + 自定义 error detail（或 `google.rpc.Status` / `google.rpc.ErrorInfo`）；HTTP 由 gateway 映射为：

```json
{
  "code": 40101,
  "message": "unauthorized",
  "data": null
}
```

- 分页（默认，可复议）：`page`（从 1）、`page_size`（默认 20，最大 100）、响应带 `total`。
- ID：对外用 `string`（内部可存 BIGINT/UUID；默认 **雪花/UUID 字符串**，可复议）。
- 时间：`google.protobuf.Timestamp` 或 Unix 秒 `int64`；默认 **int64 Unix 秒**，减少依赖（可复议）。

### 4.2 shared

建议文件：`protocol/shared/common/v1/common.proto`（包名 `aidramastic.shared.v1`，可复议）。

核心 message（MVP）：

| Message | 字段（摘要） |
|---------|----------------|
| `PageRequest` | `page`, `page_size` |
| `PageResponse` | `page`, `page_size`, `total` |
| `Empty` | — |
| `ErrorDetail`（若自定义） | `code`, `message`, `metadata` |

公共错误码区间（写入 `app/shared/errors`，proto 可只放注释）：

| 区间 | 含义 |
|------|------|
| 0 | 成功（HTTP） |
| 400xx | 参数错误 |
| 401xx | 未登录 / Token 无效 |
| 403xx | 无权限 |
| 404xx | 资源不存在 |
| 409xx | 冲突（如用户名已存在） |
| 500xx | 内部错误 |
| 503xx | 依赖不可用 |

### 4.3 user/v1 — 核心 RPC / Message

| RPC | 请求要点 | 响应要点 |
|-----|----------|----------|
| `Register` | `username`, `password`, `nickname?` | `user_id`, `access_token`, `expires_at` |
| `Login` | `username`, `password` | 同上 |
| `Logout` | （从 metadata 取 token） | `Empty` |
| `GetProfile` | （当前用户） | `User` |
| `UpdateProfile` | `nickname?`, `avatar_url?`, `bio?` | `User` |
| `UploadAvatar` | MVP：`avatar_url` 字符串字段即可 | `User` |

`User`：`id`, `username`, `nickname`, `avatar_url`, `bio`, `created_at`, `updated_at`

### 4.4 drama/v1 — 核心 RPC / Message

| RPC | 说明 |
|-----|------|
| `CreateProject` | 创建项目 |
| `ListProjects` | 当前用户项目分页 |
| `GetProject` | 详情 |
| `CreateChapter` | 隶属 project |
| `ListChapters` | 按 project |
| `UpdateChapter` | 标题/正文/状态 |
| `DeleteChapter` | 软删（默认） |
| `ListCharacters` | 按 project 或 chapter |
| `ListScenes` | 同上 |
| `ListStoryboards` | 按 chapter |
| `GetStoryboard` | 含 shots 摘要 |

核心 message 字段（够 stub 用）：

- `Project`：`id`, `user_id`, `title`, `description`, `cover_url`, `status`（`draft/active/archived`）, `created_at`, `updated_at`
- `Chapter`：`id`, `project_id`, `title`, `content`, `sort_order`, `status`（`draft/extracted/storyboarded/...`）, timestamps
- `Character`：`id`, `project_id`, `chapter_id?`, `name`, `description`, `attributes_json`, `image_asset_id?`
- `Scene`：`id`, `project_id`, `chapter_id?`, `name`, `description`, `image_asset_id?`
- `Dialogue`：`id`, `chapter_id`, `character_id?`, `content`, `sort_order`
- `Storyboard`：`id`, `chapter_id`, `title`, `status`, `shots[]`
- `Shot`：`id`, `storyboard_id`, `sort_order`, `prompt`, `dialogue_ref?`, `video_asset_id?`, `status`
- `Asset`：`id`, `project_id`, `kind`（`character_image/scene_image/shot_video/...`）, `url`, `meta_json`

### 4.5 ai/v1 — 核心 RPC / Message

| RPC | 说明 |
|-----|------|
| `ExtractChapterAssets` | 入参：`chapter_id`, `content`（或 drama 侧已有正文由调用方传入）；出参：`job_id` |
| `GenerateCharacterImage` | `character_id`, `prompt?`, `capacity?` → `job_id` |
| `GenerateSceneImage` | 同上 |
| `SplitStoryboards` | `chapter_id`, `content?` → `job_id` |
| `GenerateShotVideo` | `shot_id`, `prompt?` → `job_id` |
| `GetJob` | `job_id` → `Job` |
| `ListJobs` | 过滤 `project_id?`, `status?` + 分页 |

`Job`：

- `id`, `user_id`, `project_id?`, `type`（`extract/character_image/scene_image/split/shot_video`）
- `status`：`pending` | `running` | `succeeded` | `failed`
- `capacity`：选用的 yaml capacity 名
- `request_json`, `result_json`（stub 结构见下）, `error_message`
- `created_at`, `updated_at`, `finished_at?`

Stub `result_json` 示例：

```json
{
  "characters": [{"name": "主角", "description": "stub"}],
  "scenes": [{"name": "教室", "description": "stub"}],
  "dialogues": [{"speaker": "主角", "content": "你好"}],
  "asset_url": "https://example.invalid/stub/character.png",
  "storyboards": [{"title": "镜1", "shots": [{"prompt": "stub shot"}]}]
}
```

---

## 5. AI 可插拔配置（重点）

### 5.1 YAML 完整示例（可抄）

```yaml
ai:
  providers:
    - element_type: llm        # llm | image | video
      capacity: mock-llm       # 模型/能力名，业务按此选择
      enabled: true
      driver: mock             # 实现驱动：mock | openai | seedance | keling | ...
      params:                  # 自由 map，代码可校验也可透传
        timeout_ms: 60000
        temperature: 0.7
    - element_type: image
      capacity: mock-image
      enabled: true
      driver: mock
      params:
        size: "1024x1024"
    - element_type: video
      capacity: mock-video
      enabled: true
      driver: mock
      params:
        duration_sec: 5
```

业务调用时：未显式传 `capacity` 则取该 `element_type` 下第一个 `enabled: true` 的条目（默认决策，可复议）。

### 5.2 Registry 设计

- Key：`(element_type, capacity) -> Provider`
- 加载：启动时 + 热更时重建；仅 `enabled: true` 入注册表。
- 接口建议（Go）：

```go
type LLMProvider interface {
    ExtractAssets(ctx context.Context, req ExtractRequest) (ExtractResult, error)
}

type ImageProvider interface {
    GenerateImage(ctx context.Context, req ImageRequest) (ImageResult, error)
}

type VideoProvider interface {
    GenerateVideo(ctx context.Context, req VideoRequest) (VideoResult, error)
}
```

或统一 `Provider` + 类型断言；**默认采用三分接口**，类型更清晰（可复议）。

- Driver 工厂：`map[string]Factory`，`driver` 字段选工厂；`mock` 必须内置。
- 新增厂商：实现对应接口 + 注册 factory + yaml 加一条；业务零改或极少改。
- 热更：`fsnotify`/轮询 watch yaml → 重建 registry；**解析或校验失败则保留旧 registry 并打错误日志**。

### 5.3 与 Job 的关系

1. RPC 入队写 `ai_jobs`（status=pending）。
2. Worker（同进程 goroutine）取任务 → Registry 取 Provider → 调 stub。
3. 成功：写 `result_json` + status=succeeded；失败：status=failed + error_message。
4. MVP 不做跨服务事务；drama 侧资产回写由调用方完成。

---

## 6. 配置与热更

### 6.1 各服务独立 yaml

建议路径（TODO 落地）：

```
configs/
  gateway.yaml
  user-svc.yaml
  drama-svc.yaml
  ai-svc.yaml
```

### 6.2 公共字段示意

```yaml
server:
  grpc_addr: ":9001"
  http_addr: ":8000"   # 仅 gateway

mysql:
  dsn_env: MYSQL_DSN   # 密钥走 env 引用：yaml 写 env key 名

redis:
  addr_env: REDIS_ADDR
  password_env: REDIS_PASSWORD

jwt:
  secret_env: JWT_SECRET
  expire_sec: 86400

log:
  level: info
  format: json

# ai-svc 额外：见第 5 节 ai.providers
downstream:            # gateway
  user_grpc: "127.0.0.1:9001"
  drama_grpc: "127.0.0.1:9002"
  ai_grpc: "127.0.0.1:9003"
```

### 6.3 shared/config

- `Load(path) (*Config, error)`
- `Watch(path, onChange)`：成功则 `atomic.Value` 替换；失败保留旧值。
- MySQL/Redis 连接：DSN 热更后**默认不强制重连池**（MVP）；仅 AI registry / JWT secret 等逻辑配置热更生效。连接池热更标为可复议增强。

---

## 7. 数据模型（MVP 表级）

共性字段：`id`（BIGINT/CHAR）、`created_at`、`updated_at`、`deleted_at`（软删可选，章节/项目默认启用）。

| 表 | 关键列 |
|----|----------|
| `users` | `username` UNIQUE, `password_hash`, `nickname`, `avatar_url`, `bio` |
| `projects` | `user_id`, `title`, `description`, `cover_url`, `status` |
| `chapters` | `project_id`, `title`, `content` TEXT, `sort_order`, `status` |
| `characters` | `project_id`, `chapter_id` NULL, `name`, `description`, `attributes_json`, `image_asset_id` |
| `scenes` | 同角色结构偏场景 |
| `dialogues` | `chapter_id`, `character_id` NULL, `content`, `sort_order` |
| `storyboards` | `chapter_id`, `title`, `status` |
| `shots`（可并入 storyboards JSON；默认**独立表**便于视频任务关联，可复议） | `storyboard_id`, `sort_order`, `prompt`, `video_asset_id`, `status` |
| `assets` | `project_id`, `kind`, `url`, `meta_json` |
| `ai_jobs` | `user_id`, `project_id`, `type`, `status`, `capacity`, `request_json`, `result_json`, `error_message`, `finished_at` |

索引建议：`projects(user_id)`、`chapters(project_id)`、`ai_jobs(status, created_at)`、`users(username)`。

迁移工具：默认 **golang-migrate** 或 embed SQL（可复议）；首版可手写 `scripts/sql/001_init.sql`。

---

## 8. 主流程（状态机简述）

```
登录 → 建项目 → 写章节(draft)
     → ExtractChapterAssets (mock job → succeeded)
     → 调用方把角色/场景/台词写入 drama（status: extracted）
     → GenerateCharacterImage / GenerateSceneImage
     → 回写 asset_url
     → SplitStoryboards → 写入 storyboards/shots
     → GenerateShotVideo → 回写视频 asset
```

每步 MVP：mock job **立即或短延迟成功**。章节 `status` 枚举默认：`draft` → `extracted` → `imaged` → `storyboarded` → `video_ready`（可复议，前端也可只看任务状态）。

---

## 9. API 与鉴权

- JWT：HS256，claims 含 `sub`(user_id)、`jti`、`exp`。
- gateway 校验签名 + Redis 黑名单；下游可信内网，仍建议透传 `x-user-id` 并由服务二次校验（防误调；MVP 可只信 gateway，可复议）。
- CORS：开发环境放行 `localhost` Vite 端口。

---

## 10. 前端（web）范围

| 路由 | 页面 | MVP 要求 |
|------|------|----------|
| `/login` | 登录/注册 | 调 API，存 token |
| `/profile` | 个人中心 | 展示/改昵称头像 URL |
| `/projects` | 项目列表 | 列表 + 创建 |
| `/projects/:id/chapters` | 章节列表/编辑 | 文本编辑 + 触发 Extract |
| `/projects/:id/assets` | 资产列表 | 空表 + 假数据绑定 API |
| `/projects/:id/storyboards` | 分镜列表 | 同上 |

技术默认：Vue3 + Vue Router + Pinia + Axios（可复议为 fetch）；包管理 pnpm（可复议 npm）。

---

## 11. 本地运行（规划）

1. 起 MySQL、Redis（docker-compose 可选）。
2. `make gen` 生成 pb。
3. 分别启动 user / drama / ai / gateway。
4. `cd web && pnpm dev`。

具体命令写入仓库根 README（TODO 任务 K）；本 PRD 不改根 README，除非执行阶段需要。

---

## 12. 默认决策一览（可复议）

| # | 决策 |
|---|------|
| D1 | HTTP BFF 手写，不用 grpc-gateway |
| D2 | AI 结果回写由 gateway/前端串行，ai-svc 不依赖 drama |
| D3 | ID 对外 string；时间 int64 Unix 秒 |
| D4 | 密码 bcrypt；JWT HS256 + Redis jti 黑名单 |
| D5 | Provider 三分接口 LLM/Image/Video |
| D6 | 未指定 capacity 时用该 element_type 首个 enabled |
| D7 | shots 独立表；软删用于 project/chapter |
| D8 | 配置热更：逻辑配置生效；DB 连接池不热切 |
| D9 | 前端 Vue3 + Pinia + Axios + pnpm |
| D10 | media 独立服务不做；媒体状态在 ai + drama |
| D11 | 可观测：自研 traceService（SQLite + HTTP ingest）；不做 Jaeger/ELK 依赖 |
| D12 | 各服务日志默认 HTTP `POST /api/v1/logs/ingest` 推到 traceService；本地也可文件尾随采集 |

---

## 13. 相关文档

- 开发规范：同目录 `CODING_STANDARDS.md`；仓库根 `AGENTS.md`（Agent/工程宪法，冲突时产品级约定以 AGENTS 优先说明）
- 落地清单：同目录 `TODO.md`
- 可观测子系统：`traceService/README.md`、`traceService/docs/PLAN.md`
