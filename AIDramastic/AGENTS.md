# AGENTS.md — AIDramastic 编码与工程宪法

> 给 **Cursor / AI Agent / 人类** 直接遵守的规则。条目可执行；细节与示例见 `docs/prd-20260927-init-service/CODING_STANDARDS.md`。  
> **冲突时**：产品级约定（trace_id、可插拔 AI、错误不 panic、与 traceService 边界）以**本文件**优先说明；实现细节以本文件 + CODING_STANDARDS 为准。

---

## A. 总则

1. 技术形态：**Go 微服务**（gateway HTTP BFF + user/drama/ai gRPC）+ **Vue3** 主前端。
2. 业务错误**只** `return error`，**禁止**用 panic 做控制流；库代码禁止 panic。
3. 配置使用 **YAML**，支持**热更新**；解析/校验失败必须保留旧配置并打 Error 日志。
4. AI 能力按 YAML 的 `element_type` / `capacity` / `driver` **可插拔**注册；业务只调 Provider 接口，禁止把厂商 SDK 写死在 service 层。
5. MVP 阶段真实 AI / 支付 / 完整 APM **不做**；mock/stub + 规范 + 可观测约定先行。

---

## B. 错误处理（定死）

1. 业务路径：只 `return error`（或包装后的 error）向上传。
2. **禁止**在 `app/shared/**`、`internal/**` 内 `panic`；禁止用 panic 做分支。
3. 仅 `main` 启动阶段：致命配置/依赖失败允许 `log.Fatal` / `os.Exit(1)`。
4. 统一业务错误类型 `BizError{Code int, Message string}`（见 `app/shared/errors`）。
5. Handler 负责映射：
   - gRPC：`status` + 业务 detail（码段见 PRD / CODING_STANDARDS）
   - HTTP（gateway）：统一体 `{ "code", "message", "data" }`
6. 未知 error → 500 / Internal，**必须打日志**，不得把 stack 明文返回客户端。

---

## C. 分层

```
handler (gRPC/HTTP) → service → repo
                         ↘ adapter（第三方 / AI Provider）
```

| 层 | 职责 | 禁止 |
|----|------|------|
| handler | 参数校验、鉴权提取、DTO/proto 转换、错误映射 | SQL、调外部 AI |
| service | 业务编排、事务、状态机 | 直连厂商 SDK |
| repo | MySQL / Redis | 调外部 HTTP AI、依赖 service |
| adapter | AI driver、外部客户端；注册到 Registry | 反向依赖 handler |

禁止 handler 直访 DB；禁止 repo 依赖 service。Provider 实现一律放 **adapter**。

---

## D. 可观测性（重点）

### D.1 trace_id 强制

1. 每个 HTTP / gRPC 请求**必须**有 `trace_id`（UUID 字符串）。
2. 客户端可传请求头 `X-Trace-Id`；**没有则由 gateway / 入口服务生成**。
3. 向下游透传：
   - gRPC metadata：`trace_id`（及 `x-user-id`）
   - HTTP header：`X-Trace-Id`（及用户身份相关头，按 gateway 约定）
4. 入口中间件写入 context；出站客户端从 context 读出并注入。

### D.2 结构化日志字段（每条必带）

| 字段 | 说明 |
|------|------|
| `trace_id` | 全链路 ID |
| `service` | 服务名，如 `gateway` / `user-svc` |
| `level` | DEBUG / INFO / WARN / ERROR |
| `msg` / `message` | 日志正文 |
| 时间 | ISO8601 或 Unix；推荐带时区，如 `2026-09-27T22:00:00+08:00` |

推荐：**JSON 一行一条**。可选：`span_id`、`user_id`、`method`、`err`、自定义 `fields`。

### D.3 日志如何进入 traceService（默认定死）

**默认（MVP）**：各服务将 JSON 日志通过 HTTP 推到 traceService：

- 单条或批量：`POST /api/v1/logs/ingest`
- 本地开发也可用：写到约定目录 + 文件尾随采集（实现细节见 `traceService/docs/PLAN.md`）

禁止「必须先起 Jaeger / ELK 才能开发」。**traceService 可独立先做**，不阻塞主业务服务脚手架。

### D.4 查日志

打开 **traceService Web**，输入 `trace_id`，查看跨服务日志时间线（按时间排序）。

### D.5 脱敏

密码、JWT 全文、密钥、DSN 密码、用户隐私正文：**不得**明文落日志。

---

## E. 配置

1. 各服务独立 YAML（示例放仓库根 `configs/*.yaml` 或 `configs/*.example.yaml`）。
2. 热更：`Load` + `Watch`；成功则原子替换快照；失败保留旧值。
3. 密钥字段只写 **env 名**（如 `secret_env: JWT_SECRET`），程序 `os.Getenv`；禁止提交真实密钥。
4. AI providers 热更失败时保留旧 Registry。

---

## F. Proto

1. **先改** `protocol/**/*.proto`，再执行 `make gen`（或仓库规定脚本）。
2. **禁止手改** `*.pb.go` / `*_grpc.pb.go`。
3. 包名：`aidramastic.<domain>.v1`；RPC 名 VerbNoun。

---

## G. 前端（主业务 web）

1. Vue3 + Vue Router + Pinia；HTTP 客户端默认 Axios。
2. API 错误体约定：`{ code, message, data }`。
3. 请求头必须带：
   - `Authorization: Bearer <token>`（需登录接口）
   - `X-Trace-Id: <uuid>`（每次请求；可本地生成并贯穿一次用户操作）
4. 环境变量用 `VITE_*`；不把密钥写进前端仓库。

---

## H. 安全

1. 不提交：`.env`、真实密钥、`*.pem`、生产 DSN、secrets/。
2. 日志脱敏（见 D.5）。
3. 下游服务信任内网仍建议透传并校验 `x-user-id`（MVP 可简化，但接口先留好）。

---

## I. 与 traceService 的关系

1. `traceService/` 是**独立子系统**（Python FastAPI + 自有 Vue3 + MVP SQLite），可单独开发联调。
2. 主仓业务服务只通过**约定协议**上报日志（HTTP ingest 或文件约定）；**禁止** `import` traceService 源码。
3. 主业务 Go 服务未就绪时，也可先用模拟脚本往 traceService ingest，验证查询 Web。
4. 不把完整 APM / Jaeger 集群当作 MVP 依赖。

---

## 快速检查清单（改代码前扫一眼）

- [ ] 错误是 return，不是 panic？
- [ ] 请求有 `trace_id` 且向下透传？
- [ ] 日志 JSON 含 `trace_id` + `service` + `level` + `msg` + 时间？
- [ ] 改了 proto 是否只改源文件并 gen？
- [ ] AI 新厂商是否只加 driver + yaml，未污染 service？
- [ ] 有无密钥进仓库 / 进日志？
