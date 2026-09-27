# traceService

轻量 Trace / 日志查询：**FastAPI API + Python Worker + Go Worker + Redis + SQLite**。

## 架构

```
POST /api/v1/logs/ingest → Redis trace:ingest
  → worker_py normalize → Redis trace:persist
  → Go worker batch INSERT SQLite + DEL cache
GET /api/v1/logs?trace_id= → cache → SQLite
GET /healthz → {status:ok}
```

## 本地启动

```bash
# 0. Redis
redis-server   # 或系统服务

# 1. API（默认 :8100）
cd traceService
./run.sh
# 首次会创建 backend/.venv 并 pip install

# 2. Workers
./mq.sh start
./mq.sh status

# 3. 可选 mock
python backend/scripts/gen_mock_logs.py
```

健康检查：`curl -s http://127.0.0.1:8100/healthz`

### ingest 示例

```bash
curl -s -X POST http://127.0.0.1:8100/api/v1/logs/ingest \
  -H 'Content-Type: application/json' \
  -d '{"logs":[{"trace_id":"11111111-1111-1111-1111-111111111111","service":"gateway","level":"INFO","message":"hi","timestamp":"2026-09-27T22:00:00+08:00"}]}'
```

### query 示例

```bash
curl -s 'http://127.0.0.1:8100/api/v1/logs?trace_id=11111111-1111-1111-1111-111111111111'
```

## 测试

```bash
cd backend && .venv/bin/pytest
cd ../worker_py && PYTHONPATH=. ../backend/.venv/bin/pytest
cd ../worker && go test ./...
```

## 目录

| 路径 | 说明 |
|------|------|
| `backend/` | FastAPI（ingest 只入队 + query 只读） |
| `worker_py/` | Python Worker（规范化） |
| `worker/` | Go Worker（唯一 SQLite 写者） |
| `run.sh` / `mq.sh` | API / Worker 启停 |
| `plans/` | 需求计划四件套 |

## 约束

- ingest **禁止**写 SQLite
- 主业务 MySQL ≠ 本服务 SQLite
- 不依赖 Jaeger / ELK
