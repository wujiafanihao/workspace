# baiduWiki 前端（阶段一 · mock）

Vue 3 + Vue Router + Vite（TypeScript）。阶段一只读本地 mock，不连接 FastAPI / 百度。

## 启动

```bash
cd /Users/mac/Desktop/Project/workspace/baiduWiki/web
npm install
npm run dev
```

浏览器打开终端提示的本地地址（默认 `http://127.0.0.1:5173`）。

## 构建

```bash
npm run build
```

## 路由

| 路径 | 页面 |
|------|------|
| `/` | 首页（统计 / 热词 / 动态 / 历史上的今天 / 模块区块） |
| `/search?word=` | 搜索结果 |

## mock → API 切换（阶段二）

1. 编辑 `.env.development`（或 `.env`）：
   - `VITE_DATA_MODE=api`
   - `VITE_API_BASE=https://your-api.example`
2. `src/api/home.ts` / `src/api/search.ts` 已按 `isMockMode()` 分支；切到 `api` 后走 `fetch`。
3. 组件字段解构保持不变（合同稳定前提下）。

## 目录要点

- `src/mock/*.json` — fixtures
- `src/api/` — 数据层抽象
- `src/components/` — 首页 / 搜索组件

## 环境变量

参见 `.env.example`（`VITE_DATA_MODE=mock`）。真实 `.env.*` 已被工作空间 gitignore。

## 主题（亮 / 暗）

- Token 唯一来源：`src/styles/tokens.css`（`data-theme=light|dark`）
- 逻辑：`src/theme/`（`useTheme` / `bootstrapTheme`）
- 顶栏「日/月」切换；选择写入 `localStorage`（`baiduwiki-theme`）
- 组件禁止硬编码色值，只使用 `var(--*)`，保证亮暗都能看清字色
