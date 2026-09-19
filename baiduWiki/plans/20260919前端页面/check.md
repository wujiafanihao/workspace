status: archive

# 验收清单：前端页面（20260919）

允许 status：`in_progress` | `complete` | `tests` | `archive`

流转：`in_progress` → `complete` → `tests` → `archive`（本需求已到 archive，可提交）

## 阶段一 · 文档与 mock

- [x] 文档明确 Phase 1 **MAY mock / 不要求真后端**
- [x] 路由与组件列表完整
- [x] mock 形状与搜索/首页合同对齐
- [x] mock→API 切换说明已评审
- [x] todo A/B 完成（可选 MCP 收缩字段：延期，不挡阶段一）

## 阶段一 · 工程实现

- [x] 首页可展示 mock 模块
- [x] 搜索页可展示 mock 列表 / 空态
- [x] 未误接百度或未文档化的外网 BFF
- [x] `npm run build`（`vue-tsc -b && vite build`）本机通过，exit 0（2026-09-19 再验）

## 协议自检（archive 前）

- [x] 目录清晰：`baiduWiki/web` 按 views/components/api/mock 分层
- [x] README 写明 `npm run dev` / mock→API 切换
- [x] `.env.development` 不进仓（工作空间 `.gitignore`）；提供 `.env.example`
- [x] 无 FastAPI / 无百度 token 依赖

## 阶段二（延期 · 不挡本需求 archive）

- [ ] 真 API 联调
- [ ] 错误码与合同一致
- [ ] （pending）切 API，去掉对 mock 的硬依赖

## 备注

- 工程：`baiduWiki/web/`
- mock：`src/mock/{home,search}.json`
- 线框：design.md §5
- 归档说明：阶段一范围已交付；阶段二单开迭代，不阻塞本次 commit
