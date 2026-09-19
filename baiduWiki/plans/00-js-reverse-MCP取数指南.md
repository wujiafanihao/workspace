# js-reverse MCP 取数指南（百科类页面）

> 面向小白、步骤尽量细。工具服务器名：**`user-js-reverse`**（界面里也可能显示为 **js-reverse**）。
> 目标：打开百科类页面 → 复现操作 → 从网络面板里找到 API → 把响应 JSON 导出到本地文件。
> **用途边界**：观察字段与交互，服务「等价产品」设计；**生产数据请走自建 CMS/DB**，见文末伦理与合规。

相关文档：

- 本目录索引：[README.md](./README.md)
- 既有分析：[`../docs/python/baiduWiki/`](../../docs/python/baiduWiki/)（01–04）
- 下游计划：[20260919搜索等价](./20260919搜索等价/) · [20260919首页同步](./20260919首页同步/) · [20260919前端页面](./20260919前端页面/)

---

## 0. 这篇教你做什么 / 不做什么

### 做什么

1. 确认 MCP 已连接。
2. 用真实工具名走一遍：**开页 → 清空网络 → 复现 UX → 列表过滤 → 按 reqid 导出 body**。
3. 需要时再看请求头 / token、调用栈、断点、源码搜索、截图。
4. 对照「百科已知端点（仅参考）」知道该搜哪些 URL 子串。
5. 学会怎么向 Agent 下一句有效指令。

### 不做什么

- 不教你写爬虫长期刮百度 CDN。
- 不把 `x-bk-token` 当生产密钥方案。
- 不在本指南里贴完整业务响应隐私数据（导出到你自己的文件即可）。

---

## 1. 前置条件（做之前先勾）

1. Cursor / Grok Bot 侧 MCP 已添加并启用 **js-reverse**，服务器标识一般为 **`user-js-reverse`**。
2. 工具列表里能看到至少这些名字（名字必须对上，不要凭感觉换工具）：
   - `new_page` / `navigate_page`
   - `clear_network_requests`
   - `click_element`
   - `list_network_requests`
   - `get_request_initiator` / `break_on_xhr` / `get_paused_info`
   - `evaluate_script` / `search_in_sources` / `take_screenshot`
3. 你有一个目标 URL（示例）：`https://baike.baidu.com/`
4. 心理预期：
   - **捕获不是回溯的**：MCP 附着之后才开始记请求；更早的流量要 **reload / 再点一次** 才会进队列。
   - 队列大约 **5000** 条 FIFO；太久以前的 reqid 可能被挤掉，需要再 list 一次。

---

## 2. 标准流程（推荐照抄）

下面每一步都写「工具名 + 关键参数 + 你期望看到什么」。

### 步骤 1 — 打开目标页

二选一：

**A. 新开一页（推荐，不弄乱当前页）**

- 工具：`new_page`
- 参数：`url = "https://baike.baidu.com/"`
- 行为：等 DOMContentLoaded（不一定等齐所有图片），并把该页设为后续工具的「当前页」。

**B. 在当前已选中的页里跳转**

- 工具：`navigate_page`
- 参数：`type = "url"`，`url = "https://baike.baidu.com/"`  
  （只给 `url` 时通常也会按跳转处理；`type` 还可取 `reload` / `back` / `forward`。）

**你期望**：页面标题/地址变成百科首页；之后所有 `list_network_requests` 都针对这一页。

### 步骤 2 —（可选但强烈建议）清空网络捕获

- 工具：`clear_network_requests`
- 参数：`confirm = true`（**必须为 true**，否则不会清）
- 作用：丢掉当前页已捕获的 HTTP 证据（请求队列、响应体缓存、initiator 映射）。
- **不会**清：Cookie、站点存储、HTTP 缓存、控制台日志。若要干净登录态，另用 `clear_site_data`（同样要 `confirm=true`，且不可逆）。

**何时清**：你马上要点搜索 / 点模块，希望列表里「全是这次操作」触发的请求时。

### 步骤 3 — 复现用户操作（让接口真正打出来）

常见两种：

1. **搜索**：在搜索框输入词并提交（可用页面内交互；需要点按钮时用 `click_element`）。
2. **点首页模块 / 热词 / 卡片**：同样用 `click_element`。

`click_element` 要点：

| 参数 | 说明 |
|------|------|
| `selector` | 当前 **选中 frame** 内的 CSS 选择器；若在 iframe 里，先 `select_frame` |
| `confirm` | **必须 `true`**（点击可能提交/跳转） |
| `index` | 选择器命中多个时，显式给 0-based 下标 |
| `button` | 默认 `left` |

不会「猜」点哪个；选不到或不可见会失败——这时用 `take_screenshot` 看一眼再改 selector。

也可以不用点击，而用 `navigate_page` 直接打开带 query 的搜索结果 URL（若你已知）。

### 步骤 4 — 列出并过滤网络请求

- 工具：`list_network_requests`
- 常用过滤（可组合，**条件之间是 AND**；同一过滤多值是 OR）：

| 参数 | 百科取数常用值 | 含义 |
|------|----------------|------|
| `urlFilter` | `"/lemma/api/"` | URL **包含**该子串 |
| `resourceTypes` | `["xhr","fetch"]` | 只要 XHR/Fetch，去掉图片脚本噪音 |
| `methods` | `["GET"]` 或 `["POST"]` | HTTP 动词 |
| `pageSize` / `pageIdx` | 默认约 20 / 从 0 起 | 翻页 |

**示例意图**：只要词条 API 的 xhr/fetch：

- `urlFilter="/lemma/api/"`
- `resourceTypes=["xhr","fetch"]`

**你期望**：得到一张表，每行有 **reqid**、方法、URL、状态码等。把目标行的 **reqid** 抄下来。

### 步骤 5 — 按 reqid 导出 JSON（最重要）

再次调用 `list_network_requests`，这次带上：

| 参数 | 建议 |
|------|------|
| `reqid` | 上一步抄的数字 |
| `outputFile` | 本地路径，如 `./exports/baike-home-module.json` 或绝对路径 |
| `outputPart` | 导出响应体用 **`responseBody`**；只要头用 `responseHeaders`；整包用 `all`（默认） |
| `confirmOverwrite` | 若文件已存在，必须 `true` |

**你期望**：工具返回「写到了哪个绝对路径」；用编辑器打开，应是（或包含）JSON。

小白口诀：

> 先 list 找 **reqid** → 再 list 一次带 **reqid + outputFile + outputPart=responseBody**。

### 步骤 6 — 需要请求头 / token 时

1. 对同一 `reqid` 导出 `outputPart="responseHeaders"` 或 `all`，看响应头。
2. 在 `all` / 请求详情里看 **请求头**（观察是否出现 `x-bk-token` 等）。
3. **笔记级结论（观察，不是生产方案）**：
   - 浏览器里搜：`GET /lemma/api/search?word=` 往往需要页面上下文里的 **`x-bk-token`**。
   - 裸 `curl` 不带浏览器上下文时，常见业务码 **`10003`**（可理解为鉴权/上下文不足一类）。
   - 命中敏感词等策略时，可能见到 **`1001`**。
4. 把「字段形状」记到自建合同里；**不要**设计成线上依赖百度 token。

### 步骤 7 — 更深一层（可选）

按「先浅后深」：

| 目的 | 工具 | 怎么用 |
|------|------|--------|
| 谁发起的请求（不暂停） | `get_request_initiator` | 参数名是 **`requestId`**（填 list 得到的 reqid）。无栈时：再复现一次，或改用断点。 |
| 断在发请求前看参数 | `break_on_xhr` | `url` 用 **URL 子串**（尽量窄，如 `/lemma/api/search`）；**先设断点再复现**。 |
| 断住后看调用栈/作用域 | `get_paused_info` | 只读当前暂停态；不负责创建暂停。 |
| 跑一小段页面 JS | `evaluate_script` | 传 `function`（如 `() => document.title`）；可能改页面时要 `confirm=true`。 |
| 在已加载 JS 里搜字符串 | `search_in_sources` | 搜函数名、路径、token 字面量等。 |
| 肉眼确认 UI | `take_screenshot` | 布局、弹层、选择器是否点对。 |

相关配套：

- `list_breakpoints` / `remove_breakpoint`：管理断点
- `pause_or_resume`：显式暂停或继续（`action` 区分；不是隐式 toggle）
- `step`：暂停后单步
- `get_script_source` / `save_script_source`：读/存脚本片段
- `select_page` / `select_frame`：多 Tab / iframe 时先选对上下文
- `list_console_messages`：页面报错

---

## 3. 百科已知端点（仅参考，会变）

> 来自此前观察，**随时可能改**。正式字段以你当次 `outputFile` 导出为准；计划阶段用 MCP **再验一次**。

### 3.1 首页相关

| 类型 | 路径/资源（观察） | 备注 |
|------|-------------------|------|
| BFF/API | `/lemma/api/home/module` | 首页模块 |
| BFF/API | `/lemma/api/home/statistic` | 统计类 |
| BFF/API | `/lemma/api/home/dynamic` | 动态类 |
| CDN JSON | `hotLemmas.json`（CDN） | 热词一类静态/半静态 |
| CDN JSON | `eventsOnHistory/MM.json` 一类 | 历史上的今天等 |

过滤提示：`urlFilter` 可试 `"/lemma/api/home"`、`"hotLemmas"`、`"eventsOnHistory"`。

首页模块如何映射到自建存储：见计划 [20260919首页同步](./20260919首页同步/) 与 docs **02**。

### 3.2 搜索相关

| 项 | 观察结论 |
|----|----------|
| 接口 | `GET /lemma/api/search?word=` |
| 浏览器 | 常带 `x-bk-token` 等上下文头 |
| 裸 curl | 易出现业务码 **10003** |
| 敏感词等 | 可能 **1001** |

自建等价搜索合同：见 [20260919搜索等价](./20260919搜索等价/) 与 docs **03**（P0）。

---

## 4. 伦理与合规（必读）

1. **观察 ≠ 生产依赖**  
   用 MCP 看清「用户点了什么、返回了哪些字段」，是为了做**体验等价**的自有产品。
2. **生产数据默认自建**  
   词条、首页模块、热词等应由 **自有 CMS / DB / 同步任务写入的自建存储** 提供。  
   不要把「长期刮百度 token / CDN」写成默认架构（搜索与首页同步计划均按此约束）。
3. **合规笔记**  
   第三方站点 ToS、版权、隐私与频率限制需自行评估；本指南不提供绕过鉴权或批量抓取方案。
4. **导出文件**  
   导出的 JSON 可能含个人信息或未公开内容，按团队规范存放，勿随意提交到公开仓库。

---

## 5. 怎么向 Agent / 自己下指令（可复制）

### 最短有效句

> 用 js-reverse 打开百科首页，导出 module 与 search 响应 JSON

### 更稳妥的细粒度句（推荐）

> 1. 用 user-js-reverse 的 `new_page` 打开 https://baike.baidu.com/  
> 2. `clear_network_requests` 且 confirm=true  
> 3. 复现一次首页加载；`list_network_requests`，urlFilter=`/lemma/api/home`，resourceTypes=xhr/fetch  
> 4. 对 module（及需要的 statistic/dynamic）reqid 导出 outputPart=responseBody  
> 5. 再清空网络，搜索一个普通词；过滤 `/lemma/api/search`，导出 search 的 responseBody  
> 6. 如有 token，另导出 responseHeaders / all，只做字段笔记，不要当生产方案

### 给「搜索等价」计划复验字段

> 对照 MCP 再验一次搜索 list item 字段，结果对齐 docs/03 与 `20260919搜索等价/design.md` 映射表

---

## 6. 故障排查速查

| 现象 | 可能原因 | 怎么办 |
|------|----------|--------|
| list 是空的 | 附着前的流量；或已 clear | `navigate_page` reload 或再点一次 |
| 找不到 `/lemma/api/` | 过滤太窄 / 实际路径变了 | 先去掉 urlFilter，只留 xhr/fetch，肉眼扫 |
| 导出失败文件已存在 | 未确认覆盖 | `confirmOverwrite=true` |
| click 失败 | 选择器命中 0 或多、或不可见 | 截图；加 `index`；检查 iframe → `select_frame` |
| initiator 无栈 | 捕获开始晚于该请求 | 再复现；或 `break_on_xhr` 后复现 |
| curl 10003 | 缺浏览器上下文 / token | 预期内；改走自建 API 设计 |
| 业务码 1001 | 敏感词等策略 | 记入合同错误码表，自建侧自行定义策略 |

---

## 7. 和三份计划怎么配合

```text
MCP 取数指南 ──观察字段/错误码──► 搜索等价 design（字段映射、P0 合同）
            ──观察首页模块──► 首页同步 design（module 表、sync_*）
            ──导出样例形状──► 前端 mock JSON（阶段一可不连真后端）
```

做完一次导出后，请到对应计划的 `todo.md` 勾选「对照 MCP 再验一次字段」类任务，并在 `check.md` 保留证据路径（导出文件名即可）。
