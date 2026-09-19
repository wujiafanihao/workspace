# 待办：前端页面（20260919）

> 阶段一：**页面 / 线框 / mock fixtures**。  
> **不要**把「绑定真实 API」列为阶段一必做。

## A. 规划与线框（当前）

- [x] 确认路由 `/`、`/search` 与产品一致
- [x] 按 [design.md](./design.md) 评审组件清单（可增删，改完同步文档）
- [x] 补全文字线框或外链线框工具链接
- [x] 与搜索/首页 design 对齐字段与 module 键名
- [x] （可选）对照 MCP 导出收缩 mock 字段 → **延期**（阶段一 mock 已够用，不挡 archive）

## B. Mock fixtures（当前）

- [x] 定义 `home` mock 形状说明（或样例 JSON 存放约定路径）
- [x] 定义 `search` mock 形状说明（成功 / 空列表）
- [x] 写明阶段一 `VITE_DATA_MODE=mock` 约定
- [x] 写明阶段二切换步骤（已在 design，需评审）

> 实现路径：`baiduWiki/web/`（`src/mock/home.json`、`src/mock/search.json`）

## C. 实现页（阶段一已落地于 `baiduWiki/web`）

- [x] 脚手架 Vue3 + Router（路径 `baiduWiki/web`）
- [x] AppShell / Header / 首页各模块组件
- [x] SearchView 列表与空态
- [x] 接入 mock 模块
- [ ] （pending·阶段二）切 API，去掉对 mock 的硬依赖

## D. 明确不做（阶段一）

- [ ] ~~绑定真实 `/api/search` `/api/home`~~（阶段二）
- [x] ~~在 baiduWiki 下创建 FastAPI 应用源码~~（未创建后端；仅前端 `web/`）
