# 待办：首页同步（20260919）

## A. 规划与文档（当前）

- [ ] 通读 docs/02 首页模块，完整抄入/校对 [design.md](./design.md) 模块表
- [ ] **对照 MCP 再验一次字段**（导出 `home/module`、`statistic`、`dynamic` 等，见 [../00-js-reverse-MCP取数指南.md](../00-js-reverse-MCP取数指南.md)）
- [ ] 确认 CDN 类资源是否仍出现在当前首页网络面板（hotLemmas / eventsOnHistory）
- [ ] 定自建表名与主键；标注 CMS 是否可人工覆盖
- [ ] 写清 Redis 聚合键与 TTL（即使 P1）
- [ ] 写清 `run.sh` / `mq.sh` 职责差异（已有草案则评审）
- [ ] 合规复核：无默认百度 token/CDN 刮取
- [ ] 与 [../20260919前端页面/design.md](../20260919前端页面/design.md) 对齐 mock `modules` 键名

## B. Mock / Fixture（当前可做）

- [ ] 为每个 module_key 准备脱敏 fixture 说明或 JSON 路径约定
- [ ] 定义聚合包样例（供前端首页 mock）

## C. 代码实现（pending · 后续）

- [ ] （pending）表迁移 / ORM 模型
- [ ] （pending）各 `sync_*` worker
- [ ] （pending）`run.sh` 可执行入口
- [ ] （pending）Redis 聚合刷新
- [ ] （pending）`GET /api/home`
- [ ] （pending）`mq.sh` / 队列消费者
- [ ] （pending）监控与失败告警

## D. 文档阶段完成定义

A+B 完成后保持 [check.md](./check.md) 为 `in_progress`，直到 C 项进入测试再改 status。
