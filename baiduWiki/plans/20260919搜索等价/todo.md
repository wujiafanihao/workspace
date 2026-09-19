# 待办：搜索等价（20260919）

说明：勾选框 `- [ ]` / `- [x]`。  
**本阶段优先：规划 / 文档 / mock 合同。** 带「代码·pending」的项等进入实现迭代再做。

## A. 规划与文档（当前）

- [ ] 通读 [`../../../docs/python/baiduWiki/`](../../../docs/python/baiduWiki/) **03** 搜索章节，摘出 P0 字段清单
- [ ] 通读 [plan.md](./plan.md) / [design.md](./design.md)，标出与 03 不一致处
- [ ] 更新 design 字段映射表（观察键 → 自建键）
- [ ] **对照 MCP 再验一次字段**（按 [../00-js-reverse-MCP取数指南.md](../00-js-reverse-MCP取数指南.md) 导出 search JSON）
- [ ] 将导出样例路径记到 [check.md](./check.md) 备注（注意脱敏）
- [ ] 与前端计划对齐 mock JSON 形状（链接 [../20260919前端页面/design.md](../20260919前端页面/design.md)）
- [ ] 合规复核：design 中无「生产默认百度 token/CDN」表述

## B. Mock 合同（当前可做，仍无业务代码）

- [ ] 编写「成功响应」fixture 说明（可放在前端 `mock/` 或本计划附件路径约定）
- [ ] 编写「空结果 / 参数错误 / 敏感拦截」三种示例形状（仅文档或 JSON 文件，非服务实现）
- [ ] 约定分页参数命名与 docs/03 一致

## C. 代码实现（pending · 后续迭代）

- [ ] （pending）FastAPI async `GET /api/search` 路由与 schema
- [ ] （pending）自建 lemma 存储查询 / 索引接入
- [ ] （pending）错误码与日志
- [ ] （pending）P1 Redis 缓存
- [ ] （pending）P1 suggest API
- [ ] （pending）单测 / 合约测试对齐 docs/03
- [ ] （pending）与前端联调，替换 mock

## D. 完成定义（文档阶段）

当 A+B 勾完，且 check.md 中「文档项」可勾选时，可将实现工作单拆到下一次迭代；**在代码完成前 check.md 保持 `status: in_progress`。**
