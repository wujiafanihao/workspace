status: in_progress

# 验收清单：首页同步（20260919）

允许 status：`in_progress` | `complete` | `tests` | `archive`

## 文档与合同

- [ ] 模块表与 docs/02 一致（含 MCP 再验备注）
- [ ] sync_* 职责与表映射清晰
- [ ] Redis 聚合草图已评审
- [ ] run.sh / mq.sh 策略已评审
- [ ] 合规：自建存储默认
- [ ] todo A/B 完成

## 代码与运行（未开始 · 保持未勾选）

- [ ] sync_* 写入自建库成功
- [ ] run.sh 本地可跑
- [ ] 聚合读取 API 或等价读径可用
- [ ] 前端真数据联调（非 mock）
- [ ] mq.sh（若启用）验收

## 备注 / 证据

- MCP 导出：
- docs/02 差异：
