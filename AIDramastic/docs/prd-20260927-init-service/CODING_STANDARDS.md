# AIDramastic 开发规范（CODING STANDARDS）

> 本文件用于定死工程约定。与 PRD 冲突时以「可运行 MVP + 本规范」为准；修改本文件需评审。  
> 产品级约定（尤其 `trace_id` / 可观测 / AI 可插拔）另见仓库根 **`AGENTS.md`**：冲突时产品级约定以 AGENTS 优先说明；实现细节以 AGENTS + 本文件为准。

---

## 1. 错误处理

- 业务错误**只**通过 `return error`（或带业务码的 error）向上传，**禁止 panic**。
- 仅 `main` 启动阶段：致命配置/依赖失败允许 `log.Fatal` / `os.Exit(1)`。
- **库代码**（`app/shared/**`、`internal/**`）禁止 `panic`；禁止用 panic 做控制流。
- Handler 层负责把 error 映射为 gRPC status / HTTP `{code,message,data}`，不得把 stack 明文返回给客户端。

---

## 2. 错误类型

- 统一在 `app/shared/errors` 定义：

```go
type BizError struct {
    Code    int    // 业务码，如 40101
    Message string
}
func (e *BizError) Error() string { /* ... */ }
```

- 提供 `New(code, message)`、`IsBiz(err)`、`Code(err)` 等辅助方法。
- 映射到 gRPC：
  - 400xx → `InvalidArgument`
  - 401xx → `Unauthenticated`
  - 403xx → `PermissionDenied`
  - 404xx → `NotFound`
  - 409xx → `AlreadyExists`
  - 500xx → `Internal`
  - 503xx → `Unavailable`
- 未知 error 一律视为 500，**必须打日志**，不得静默。

---

## 3. 日志

- 使用结构化日志（默认 zap 或 slog，项目内选定一种后全仓库统一；默认 **slog**，可复议）。
- 字段至少可带：`trace_id`（必填，等同全链路 ID；可与历史名 `request_id` 并存但优先 `trace_id`）、`user_id`、`method`、`err`；另见 §14。
- **禁止吞错**：`_ = do()` 仅允许在「明确无影响」处并注释原因。
- **敏感信息不得落日志**：密码、JWT 全文、密钥、DSN 密码、用户隐私正文可选脱敏。
- 日志级别：业务可预期错误用 `Warn`，系统异常用 `Error`。

---

## 4. Context

- 所有 RPC Handler、DB、Redis、HTTP 出站调用必须携带 `context.Context`。
- 禁止裸 `go func()` 且丢弃 cancel；派生 goroutine 必须传入可取消的 ctx，并在服务 shutdown 时收敛。
- 超时：对外 RPC/HTTP 在调用方设 timeout；DB 建议继承请求 ctx。

---

## 5. 依赖注入

- 显式构造：`NewUserService(repo, jwt, log)`，依赖从 `main` 注入。
- **禁止**全局可变单例（如可变的 `var DB *sql.DB` 随意替换）。
- 配置热更使用 `atomic.Value`（或等价无锁读）保存当前快照；读取侧 `Load()`，更新侧 `Store()`。
- Provider Registry 同样通过原子替换整体 map/结构，避免半更新。

---

## 6. 命名

- 目录名、包名：**小写**，不带下划线为佳（`usersvc` 或按目录 `user` 对应 `user-svc` 进程名）；进程目录可用 `user-svc`，Go import path 按实际 module 定。
- 导出符号清晰完整：`CreateProject`，避免 `Do`、`Handle1`。
- Proto 包名：`aidramastic.<domain>.v1`。
- 生成代码目录约定（默认，可复议）：
  - 源：`protocol/application/<domain>/v1/*.proto`
  - 生成：`protocol/gen/aidramastic/<domain>/v1/` 或 `app/shared/gen/...`——**选定后写进 Makefile，禁止混放**。
- 文件名：Go `snake` 不用；Go 文件用小写单词 `user_service.go` 可接受。

---

## 7. 分层

```
handler (gRPC/HTTP) → service → repo
                         ↘ adapter（第三方 / AI Provider）
```

- **handler**：参数校验、鉴权信息提取、DTO/proto 转换、错误映射；不含 SQL。
- **service**：业务编排、事务边界、状态机。
- **repo**：MySQL/Redis 访问；禁止在 repo 调外部 HTTP AI。
- **adapter**：AI driver、外部 HTTP 客户端；实现 Provider 接口并注册到 Registry。
- 禁止 handler 直访 DB；禁止 repo 依赖 service。

---

## 8. 测试

- 下列模块 MVP 阶段就应具备单测（可后补实现，但 PR 合入相关代码时需带测）：
  1. Provider Registry 加载 / 查找 / 禁用项
  2. config Load + Watch 失败保留旧配置
  3. BizError ↔ gRPC code 映射
- 表驱动测试优先；外部依赖用 interface mock。
- 不强制全仓库覆盖率数字；核心路径不挂「裸测」。

---

## 9. Git / 提交

- Commit 前缀：`feat:` / `fix:` / `docs:` / `refactor:` / `test:` / `chore:`。
- 示例：`feat(user-svc): add login jwt blacklist`。
- 禁止提交：真实密钥、本地 IDE 垃圾、巨大二进制、手工改过的 `*.pb.go`（见下条）。
- 分支：功能分支从主分支切；具体分支策略可复议，默认 `main` + `feat/*`。

---

## 10. Proto 变更流程

1. 先改 `protocol/**/*.proto`。
2. 执行 `make gen`（或仓库规定的 buf/protoc 脚本）生成代码。
3. **禁止手改** `*.pb.go` / `*_grpc.pb.go`。
4. 破坏性变更（删字段、改类型）需在 PR 说明兼容策略；MVP 阶段可直接改，但要同步 gateway 与 web client。

---

## 11. 配置与密钥

- YAML 中密钥类字段写 **env key 名**（如 `secret_env: JWT_SECRET`），程序 `os.Getenv`。
- **禁止**把真实密钥、生产 DSN 提交进仓库。
- 示例 yaml 可用占位：`changeme` / 空字符串 + 注释说明必填 env。
- 热更失败必须打 Error 日志并保留旧配置，不得留下半初始化状态。

---

## 12. 并发与 Redis 约定

- **JWT 黑名单**：key 建议 `auth:jwt:blacklist:{jti}`，TTL = token 剩余有效期；Logout 写入；鉴权时存在即拒绝。
- **Job 锁**（ai-svc worker）：key 建议 `ai:job:lock:{job_id}`，值 worker id，TTL 短（如 30s）并续租或完成即删；避免多实例重复执行。
- MVP 单实例时可简化锁，但接口与 key 规范先定好，便于后扩。
- Redis 命令必须带 ctx；错误要返回给调用方或记任务失败，禁止静默。

---

## 13. 补充约定（简）

- 不要在业务里 `fmt.Println` 调试后合入；用 logger。
- 公开 API 的时间与 ID 格式与 PRD 一致（string id、Unix 秒，除非已统一改）。
- 新增依赖需说明理由；优先标准库。
- Code review 关注：panic、吞错、无 ctx、手改 pb、密钥入库。


---

## 14. 可观测与 trace_id

> 权威细则与 Agent 强制规则见仓库根 [`AGENTS.md`](../../AGENTS.md) §D / §I；子系统说明见 [`traceService/`](../../traceService/)。本节省录，避免三份规范打架。

1. 每个 HTTP / gRPC 请求必须有 `trace_id`（UUID）。客户端可传 `X-Trace-Id`；缺失由 gateway / 入口生成。
2. 向下游 gRPC metadata / HTTP header 透传 `trace_id`（及 `x-user-id`）。
3. 结构化日志**每条**必须带：`trace_id`、`service`、`level`、`msg`（或 `message`）、时间；推荐 JSON 一行一条。
4. 日志进入 traceService 的 **MVP 默认**：HTTP `POST /api/v1/logs/ingest`；本地也可文件尾随采集（见 `traceService/docs/PLAN.md`）。
5. 查日志：打开 traceService Web，按 `trace_id` 看跨服务时间线。
6. **禁止**依赖 Jaeger / ELK 才能开发；主业务服务不 import `traceService` 代码。
