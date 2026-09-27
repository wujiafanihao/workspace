# check

status: archive

## 协议自检

- [x] 文件头 + 导出函数注释
- [x] 常量 / 错误码集中（constants.py / errors.py）
- [x] run.sh + mq.sh + log/
- [x] IO 异步 / Redis 池
- [x] 配对测试（*_test.py / tests/）
- [x] ingest 无 sqlite write（仅 queue XADD/LPUSH）

## 验收

- [x] pytest green：backend 19 passed；worker_py 3 passed
- [x] go test green：config + writer ok
- [x] smoke（Redis）：healthz `{status:ok}`；ingest `accepted:1`；XLEN trace:ingest=1；query 空列表（Worker 未跑）

## Smoke 记录（CST 2026-09-27 22:54）

```
redis-cli ping → PONG
GET /healthz → {"status":"ok"}
POST /api/v1/logs/ingest → {"code":0,"message":"ok","data":{"accepted":1}}
redis-cli XLEN trace:ingest → 1
GET /api/v1/logs?trace_id=... → logs:[] （符合：仅入队未落库）
```

## 剩余缺口

- Vue3 frontend 未实现（目录占位）
- 端到端双 Worker 联调未在本机长时间跑（代码已齐；可用 ./mq.sh start）
- YAML 热更 Watch 未做（MVP 不做）

## Mac smoke（CST 2026-09-27，wujiafa.local）

- healthz ok
- mq.sh start → worker_py + worker_go
- ingest accepted:2 → query 返回 2 条（gateway / user-svc，level 已规范化为大写，msg→message）
- 缺 trace_id → HTTP 400 / code 40001
- 非法 body → HTTP 400 / code 40001
- 不存在的 trace_id → logs:[]
