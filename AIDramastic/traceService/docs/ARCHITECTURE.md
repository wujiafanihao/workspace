# traceService 架构（短文）

## 定位

轻量「按 `trace_id` 查日志时间线」服务，服务本地开发与联调，**不**替代生产级 APM。

## 数据流

```
┌─────────────┐   X-Trace-Id + JSON log    ┌──────────────────┐
│ gateway     │ ─────────────────────────► │                  │
│ user-svc    │   POST /api/v1/logs/ingest │  FastAPI backend │
│ drama-svc   │                            │         │        │
│ ai-svc      │   (可选：文件尾随采集)        │         ▼        │
│ mock script │ ─────────────────────────► │      SQLite      │
└─────────────┘                            │         │        │
                                           │         ▼        │
┌─────────────┐   GET ?trace_id=           │  query API      │
│ Vue3 Web UI │ ◄───────────────────────── │                  │
└─────────────┘                            └──────────────────┘
```

1. **入口**：业务服务在处理请求时保证有 `trace_id`，打结构化 JSON 日志。
2. **上报（默认）**：HTTP 批量/单条 ingest；开发机也可用写文件 + 侧车采集（非默认）。
3. **存储**：MVP 用 SQLite 表 `logs`，按 `trace_id` 索引。
4. **查询**：Web 或 API 按 `trace_id` 拉取，按 `timestamp` 升序拼时间线。

## 边界

| 做 | 不做（MVP） |
|----|-------------|
| ingest / 按 trace 查询 / 简单 UI | 分布式采样、火焰图、全量指标 |
| 与主仓 header/JSON 约定对齐 | import 主仓 Go 代码或被主仓 import |
| 独立部署与端口 | 强依赖 K8s / Jaeger Operator |

## 与主仓关系

约定见仓库根 `AGENTS.md` §D、§I。协议变更应同时改本目录 README 与 AGENTS，避免三份文档打架。
