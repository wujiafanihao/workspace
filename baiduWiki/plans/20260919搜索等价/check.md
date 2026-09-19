status: in_progress

# 验收清单：搜索等价（20260919）

允许 status：`in_progress` | `complete` | `tests` | `archive`  
当前：**in_progress**（文档/合同阶段）

## 文档与合同

- [ ] plan.md 范围/非范围/验收已评审
- [ ] design.md P0 `GET /api/search` 与 docs/03 一致
- [ ] 字段映射表已按 MCP 再验更新
- [ ] 合规：无生产默认依赖百度 token/CDN
- [ ] todo A/B 已完成

## 代码与联调（未开始 · 保持未勾选）

- [ ] FastAPI `/api/search` 已实现
- [ ] 读自建存储，不读百度 BFF
- [ ] 合约测试通过
- [ ] 前端已切换 mock → 真 API
- [ ] Redis/suggest（若做 P1）验收

## 备注 / 证据

- MCP 导出文件：
- docs/03 差异：
- 评审人 / 日期：
