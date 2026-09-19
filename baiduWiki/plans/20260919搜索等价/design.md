# 设计：搜索等价（20260919）

> 本文是设计说明，**不含** FastAPI/Vue 源码。  
> 合同对齐：[`../../../docs/python/baiduWiki/`](../../../docs/python/baiduWiki/) **docs/03**  
> 复验手段：[../00-js-reverse-MCP取数指南.md](../00-js-reverse-MCP取数指南.md)

---

## 1. 一句话架构

```text
浏览器 / Vue
    │  GET /api/search?word=&page=&page_size=
    ▼
自建 API（规划：FastAPI async）
    │  读
    ▼
自建词条存储（DB / 检索索引）  (+ 可选 Redis 缓存 P1)
```

**禁止默认路径**：浏览器/API → 百度 `/lemma/api/search` 或依赖 `x-bk-token` / CDN 热刮。

观察百度接口只为了：**字段命名、列表结构、错误码语义** → 映射进自建合同。

---

## 2. P0 API 合同：`GET /api/search`

### 2.1 请求

| 项 | 约定（草案，最终以 docs/03 为准） |
|----|----------------------------------|
| Method | `GET` |
| Path | `/api/search` |
| Query | `word`（必填，关键词） |
| Query | `page`（可选，从 1 或 0 起——与 docs/03 统一后写死） |
| Query | `page_size` / `limit`（可选，设上限防刷） |
| Header | 自有鉴权（若需要）；**不**要求百度 token |

实现风格（后续编码时）：**FastAPI async** 路由处理函数，I/O 走 async 驱动或线程池包装，避免阻塞事件循环。

### 2.2 成功响应（形状）

与 docs/03 对齐的逻辑结构（示意，非最终 JSON 字面量）：

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "word": "用户输入",
    "total": 0,
    "list": [
      {
        "lemma_id": "自建ID",
        "title": "词条标题",
        "summary": "摘要",
        "cover": "封面URL或空",
        "url_path": "前端路由或详情path"
      }
    ]
  }
}
```

> 真实字段名以 docs/03 + MCP 再验后的映射表为准（下一节）。前端 mock 必须与此同构。

### 2.3 错误响应（语义）

| 自建 code（建议） | 语义 | 观察参考（非依赖） |
|-------------------|------|-------------------|
| 0 | 成功 | — |
| 4xx 参数错误 | word 空、超长等 | — |
| 业务「无结果」 | list 空 + total 0（也可算成功） | — |
| 自建「敏感/拦截」 | 明确文案 | 观察站可能见 **1001** |
| 自建「上游/上下文」 | 不用于百度；自建仅表示己方故障 | 观察裸 curl 常见 **10003** |

不要在自建 API 中原样依赖百度业务码；可在文档「对照表」里注释观察码。

---

## 3. 字段映射（观察 list item → 自建）

> 下表为设计模板。填写/修正时：**打开 MCP 指南导出 search JSON**，对照 docs/03，更新「观察键」列。

| 观察侧常见键（示例名，需再验） | 自建字段 | 说明 |
|--------------------------------|----------|------|
| （标题类，如 title / lemmaTitle） | `title` | 列表主标题 |
| （摘要类，如 summary / desc） | `summary` | 列表副文案 |
| （id 类，如 lemmaId / id） | `lemma_id` | 自建主键或稳定对外 id |
| （封面类，如 pic / cover） | `cover` | 可空；前端占位图策略另定 |
| （跳转类，如 url / path） | `url_path` | 指向自有详情路由 |
| （其它徽标/PV 等） | 按 P0 需要增列 | 非 P0 可砍 |

**操作步骤（给执行者）**：

1. 按 [MCP 指南](../00-js-reverse-MCP取数指南.md) 导出 `/lemma/api/search` 的 `responseBody`。
2. 打开 docs/03，核对合同字段。
3. 更新本表；若有差异，在下方「差异笔记」写清。
4. 通知前端 mock fixtures 同步改形状。

### 3.1 差异笔记（初始为空）

- （待 MCP 再验后填写）

---

## 4. P1：Redis 缓存（可选）

| 项 | 建议 |
|----|------|
| Key | `search:v1:{normalized_word}:{page}:{page_size}` |
| Value | 成功响应 `data` 的 JSON |
| TTL | 如 60–300s（按更新频率调） |
| 空结果 | 短 TTL 缓存，防穿透 |
| 失效 | 词条写入/更新时按 word 或 tag 淘汰（后期） |

P0 可不做缓存；先保证正确性。

---

## 5. P1：Suggest API（可选）

- 草图：`GET /api/search/suggest?word=`
- 返回短列表（仅 title + lemma_id），供输入框下拉。
- 可与搜索共用前缀索引；**本阶段只占位，不实现。**

---

## 6. 明确：无百度 BFF

| 允许 | 不允许（默认架构） |
|------|-------------------|
| MCP 观察字段 | 生产服务持有并转发 `x-bk-token` |
| 一次性样例 JSON 进 fixtures | 定时刮 CDN / search 当主数据源 |
| 自建 CMS 录入/导入 | 「先打百度再落库」作为唯一同步手段且无合规评估 |

首页侧同步见 [../20260919首页同步/design.md](../20260919首页同步/design.md)，同样坚持自建存储。

---

## 7. 与前端的衔接

- 阶段一前端 **mock** 本文件成功/失败 JSON 形状（见前端 design）。
- 阶段二将 `VITE_API_BASE` 等指向自建 `/api/search`， ideally **零改组件字段**（仅换数据源）。

---

## 8. 复验清单（设计层）

- [ ] MCP 导出 search 响应已发生
- [ ] 映射表观察键已替换为真实键名
- [ ] docs/03 与本文无冲突（有则记录差异笔记）
- [ ] 错误码表已与产品文案同事对齐（可稍后）
