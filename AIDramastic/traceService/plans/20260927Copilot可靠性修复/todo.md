# TODO

- [ ] plans/check in_progress
- [x] Go consumer: PEL reclaim via XAUTOCLAIM
- [x] Go consumer: shutdown flush surfaces error (non-zero exit)
- [x] Go consumer: keep pending on XAck failure + redis_msg_id idempotency
- [x] Go consumer: list reliable (processing list)
- [ ] Go consumer: maxlen
- [x] Go config: claim_min_idle_ms / claim_count
- [x] Go config: TRACE_SQLITE_PATH
- [ ] Go config: maxlen
- [x] Go writer: redis_msg_id 幂等 UNIQUE + ON CONFLICT
- [x] worker_py: PEL reclaim via XAUTOCLAIM
- [x] worker_py: list reliable (processing list)
- [x] worker_py: maxlen (persist XADD ~ MAXLEN)
- [ ] worker_py: password, no-ack-on-fail
- [x] backend: stream_maxlen on ingest XADD
- [ ] backend: password encode, strip, validation JSON, enqueue notes
- [ ] mq.sh build + pgid
- [ ] 测试 + check → archive
