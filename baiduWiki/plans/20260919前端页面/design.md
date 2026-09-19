# 设计：前端页面（20260919）

> **阶段一（Phase 1）：允许并推荐使用 mock 数据；不要求真实后端。**  
> 技术选型规划：Vue 3 + Vue Router（具体脚手架在实现迭代创建，**不在本 plans 目录写应用源码**）。

---

## 1. 路由

| Path | 页面 | 说明 |
|------|------|------|
| `/` | HomeView | 首页模块聚合 |
| `/search` | SearchView | 查询参数 `word`（及可选 `page`） |

示例：`/search?word=量子计算`

---

## 2. 组件清单（建议）

### 2.1 布局

| 组件 | 职责 |
|------|------|
| `AppShell` | 顶栏 + 主内容出口 |
| `AppHeader` | Logo、搜索框（提交跳转 `/search`） |
| `AppFooter` | 页脚链接/备案占位 |

### 2.2 首页

| 组件 | 职责 |
|------|------|
| `HomeView` | 拉取/注入 home mock，布局各模块 |
| `HomeModuleSection` | 通用模块区块（标题+槽） |
| `HotLemmasRail` | 热词 |
| `StatisticBar` | 统计 |
| `DynamicFeed` | 动态列表 |
| `EventsOnHistoryCard` | 历史上的今天 |

模块键名与 [../20260919首页同步/design.md](../20260919首页同步/design.md) 聚合 `modules` 对齐：  
`module` / `statistic` / `dynamic` / `hot_lemmas` / `events_on_history`。

### 2.3 搜索

| 组件 | 职责 |
|------|------|
| `SearchView` | 读 `word`，展示结果 |
| `SearchResultList` | 列表容器 |
| `SearchResultItem` | 单条：title / summary / cover |
| `SearchEmpty` | 空态 |
| `SearchError` | 错误态（阶段一可用假错误按钮演示） |

字段对齐 [../20260919搜索等价/design.md](../20260919搜索等价/design.md) 与 docs/03。

---

## 3. Mock JSON 形状

### 3.1 首页 `mock/home.json`（示意）

```json
{
  "version": 1,
  "updated_at": "2026-09-19T00:00:00+08:00",
  "modules": {
    "module": { "blocks": [] },
    "statistic": { "items": [] },
    "dynamic": { "list": [] },
    "hot_lemmas": { "list": [] },
    "events_on_history": { "list": [] }
  }
}
```

内部 list/block 字段在 MCP 再验 + docs/02 后填满；阶段一可用 2–3 条假数据。

### 3.2 搜索 `mock/search.json`（示意）

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "word": "示例",
    "total": 1,
    "list": [
      {
        "lemma_id": "demo-1",
        "title": "示例词条",
        "summary": "这是 mock 摘要",
        "cover": "",
        "url_path": "/lemma/demo-1"
      }
    ]
  }
}
```

阶段一 `SearchView` 可：忽略后端，直接读该文件；或按 `word` 对 `list` 做前端 filter（演示用）。

---

## 4. 数据层：mock → API 怎么换

### 4.1 建议抽象

```text
src/api/home.ts   →  getHome(): Promise<HomeAggregate>
src/api/search.ts →  search(word, page): Promise<SearchResponse>
src/api/http.ts   →  包装 fetch；读 import.meta.env.VITE_API_BASE
src/api/mode.ts   →  VITE_DATA_MODE = "mock" | "api"
```

### 4.2 切换步骤（阶段二）

1. `.env`：`VITE_DATA_MODE=api`，`VITE_API_BASE=https://your-api.example`
2. `getHome` / `search` 内 `if (mode==='mock')` 分支改为走 `fetch`${base}/api/home`` 等
3. **组件不改字段解构**（合同稳定的前提）
4. 删掉或保留 mock 作 Storybook/本地演示

阶段一验收 **不要求** 存在真实 `.env` 联调。

---

## 5. 线框（文字版）

### 5.1 首页 `/`

```text
+------------------------------------------+
| Logo          [ 搜索框.......... ] [搜]  |
+------------------------------------------+
| StatisticBar                             |
+------------------------------------------+
| HotLemmasRail  #热词 #热词 ...           |
+------------+-----------------------------+
| 主 module  |  DynamicFeed                |
| 区块...    |  条目...                    |
+------------+-----------------------------+
| EventsOnHistoryCard                      |
+------------------------------------------+
| Footer                                   |
+------------------------------------------+
```

### 5.2 搜索 `/search`

```text
+------------------------------------------+
| Header（含搜索框，回填 word）             |
+------------------------------------------+
| “以下结果关于：{word}”   共 {total} 条   |
+------------------------------------------+
| [封面] 标题                              |
|        摘要...                           |
| [封面] 标题                              |
|        摘要...                           |
+------------------------------------------+
| 空态 / 错误态                            |
+------------------------------------------+
```

---

## 6. 无障碍与基础体验（阶段一也尽量）

- 搜索框有可见 label 或 aria-label（中文产品）
- 空态给「换个词」提示
- 图片缺失用占位，不破布局
- `prefers-reduced-motion`：不做夸张入场（若加动画）

---

## 7. 与 MCP 的关系

做 mock 前可用指南导出真实形状，**脱敏后**缩成 2～3 条假数据。  
生产仍读自建 API，不在前端藏百度 token。
