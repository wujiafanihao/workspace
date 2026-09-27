# design — 实现思路

## 架构

```
POST ingest → FastAPI enqueue Redis trace:ingest
Python Worker XREADGROUP → normalize → XADD trace:persist
Go Worker XREADGROUP → batch INSERT SQLite WAL → DEL cache
GET query → Redis cache → SQLite ORDER BY timestamp ASC
```

## 模块边界

| 进程 | 写 SQLite | 职责 |
|------|-----------|------|
| FastAPI | 否（只读） | 校验、入队、查询、health |
| worker_py | 否 | 规范化、入 persist |
| worker Go | 是（唯一） | 批量落库、缓存失效 |

## 关键决策

- 队列默认 Redis Stream + 消费者组；可配置 list
- API 用 aiosqlite 只读；schema 本地 ensure 便于单测（生产由 Go Worker 建表）
- 错误体统一 `{code,message,data}`；业务码见 errors.py
- run.sh：优先 conda workspace，否则 backend/.venv
