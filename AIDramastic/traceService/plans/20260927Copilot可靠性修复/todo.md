# TODO

- [ ] plans/check in_progress
- [x] Go consumer: PEL reclaim via XAUTOCLAIM
- [x] Go consumer: shutdown flush surfaces error (non-zero exit)
- [x] Go consumer: keep pending on XAck failure + redis_msg_id idempotency
- [ ] Go consumer: list reliable, maxlen
- [x] Go config: claim_min_idle_ms / claim_count
- [ ] Go config: TRACE_SQLITE_PATH, maxlen
- [x] Go writer: redis_msg_id 幂等 UNIQUE + ON CONFLICT
- [x] worker_py: PEL reclaim via XAUTOCLAIM
- [ ] worker_py: maxlen, password, list reliable, no-ack-on-fail
- [ ] backend: password encode, strip, validation JSON, enqueue notes
- [ ] mq.sh build + pgid
- [ ] 测试 + check → archive
