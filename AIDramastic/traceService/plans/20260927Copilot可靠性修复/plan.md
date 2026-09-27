# 背景

PR #1 收到 Copilot review。经人工 triage，修复「合理」与「部分合理」项；忽略仅严重度误判、无独立代码债的部分。

## 目标

提升 stream/list 消费在崩溃/关机场景下的可靠性，并修配置与运维误导。

## 非目标

- 不改 Vue 前端
- 不做跨机分布式共识 / 完整 exactly-once
- 不引入新中间件

## 验收

- Go/Py：XAUTOCLAIM（或等价 PEL 回收）后可读 pending
- 关机 flush 失败 → 非 0 / 显式 error 日志，不谎称成功
- XAck 失败不清空 pending（或可重试）；落库侧有幂等或可安全重投
- list：可靠队列（processing list + 完成/回队）或文档+默认禁用；实现可靠路径
- XADD 带近似 MAXLEN；ingest soft_limit 不再因永不裁剪永久堵死
- TRACE_SQLITE_PATH 生效；mq.sh 管理真实 worker 进程（build 二进制或进程组）
- Redis 密码 URL 编码（Py/API）
- 校验错误 JSON 可序列化；必填字段 strip 空白
- 部分 enqueue 失败时尽量原子或返回实际 accepted + 幂等友好
- cache invalidate 失败至少打日志并有限重试
- 既有 pytest / go test 通过
