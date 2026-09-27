# plan — traceService 后台接口实现

| 字段 | 内容 |
|------|------|
| 日期 | 2026-09-27 |
| 状态 | in_progress |

## 背景

主业务多进程联调需要按 `trace_id` 查跨服务日志；不引入 Jaeger/ELK。本需求在本地 box 实现 FastAPI API + Python Worker + Go Worker 闭环，代码落在 `traceService/` 以便后续拷到 Mac。

## 一句话目标

实现 ingest 只入 `trace:ingest`、query 缓存→SQLite、双 Worker 两级队列，pytest / go test 通过。

## 范围

- backend/ FastAPI（ingest / query / healthz）
- worker_py/ 规范化消费
- worker/ Go 批量写 SQLite
- run.sh / mq.sh / plans / README

## 非范围

- Vue3 前端完整实现（仅保留目录占位）
- Jaeger / MySQL / CloudAgent / gh push

## 验收标准

1. `pytest` green（backend + worker_py）
2. `go test ./...` green（worker）
3. ingest 路径无 sqlite write
4. 若 Redis 可用：healthz + ingest smoke 成功
