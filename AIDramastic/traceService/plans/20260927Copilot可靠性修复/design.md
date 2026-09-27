# 设计

## Stream

1. 每轮先 `XAUTOCLAIM`（min-idle 可配，默认 60s）再 `XREADGROUP >`
2. XADD 使用 `MAXLEN ~ N`（配置 `maxlen`，默认与 soft_limit 同量级或独立）
3. flush 成功后再 XAck；Ack 失败保留 pending、打 error，下次仍可 claim
4. SQLite：`(trace_id, timestamp, service, level, message)` 或 `redis_msg_id` 唯一 — 优先落 `msg_id` 列（可空 list 模式）UNIQUE 防重

## List 可靠队列

- 消费：`BRPOPLPUSH`/`BLMOVE` source → `key:processing`
- 成功 flush 后 `LREM` processing
- 启动时扫描 processing 超时项回队（简化：启动全量回队到主 list）

## 关机

- Run 返回 flush error；main 非 0 退出

## 配置

- Go Load：`TRACE_SQLITE_PATH` 覆盖 sqlite.path
- mq.sh：`go build -o bin/worker` 后 nohup 二进制；`setsid`/`kill -- -$pgid`

## Python/API

- `urllib.parse.quote(password, safe="")`
- validation handler：`jsonable_encoder` 或手动剥 ctx
- Field validators strip
- enqueue：pipeline 或失败时返回已接受数并让 API 返回部分成功；优先 pipeline multi XADD + 失败不谎称全成功（已有 accepted 计数，API 可返回实际 accepted；中途失败若已写入则返回 207/业务码或仍 503 但文档说明 at-least-once — 采用：失败抛错但客户端应幂等；worker_py 侧 enqueue_persist 失败不 ACK）
