# 计划：首页同步（20260919）

> 文件夹：`baiduWiki/plans/20260919首页同步/`  
> 配套：`design.md` · `todo.md` · `check.md`  
> 取数指南：[../00-js-reverse-MCP取数指南.md](../00-js-reverse-MCP取数指南.md)  
> 模块依据：[`../../../docs/python/baiduWiki/`](../../../docs/python/baiduWiki/) **docs/02（首页模块）**

---

## 1. 动机

百科类首页通常由多个 **模块** 拼成（推荐位、热词、统计、动态、历史上的今天等）。公开站侧能观察到类似：

- `/lemma/api/home/module|statistic|dynamic`
- CDN 上的 `hotLemmas.json`、`eventsOnHistory/MM.json` 等

我们要做的是：把「首页要展示的各模块数据」**同步并沉淀到自建存储**，再由自有 API/聚合层读出给前端——而不是让生产环境默认去刮百度 CDN 或持有对方 token。

---

## 2. 目标

1. 按 docs/02 列出的模块，设计 **sync_\*** 同步工人（worker）与存储表/键。
2. 读路径：前端/BFF → **自建聚合（可 Redis）** → 自建 DB/对象存储。
3. 运行方式：先 **`run.sh` 可手动/cron 跑**；消息队列版 **`mq.sh` 留后续**。
4. 本阶段交付 **计划文档**；实现代码标 pending。

---

## 3. 范围 / 非范围

### 3.1 范围内

| 项 | 说明 |
|----|------|
| 模块清单 | 对齐 docs/02；MCP 可再验 `/lemma/api/home/*` |
| sync_* 职责表 | 每模块谁同步、写入哪张表/哪个 Redis key |
| Redis 聚合设计 | 首页一次读取的聚合结构（P0/P1 标明） |
| run.sh vs mq.sh | 启动与演进策略（文档） |
| 合规 | 自建存储默认；观察用 MCP，生产不默认 CDN 热刮 |

### 3.2 非范围

| 项 | 说明 |
|----|------|
| 工人/API 源码 | pending |
| 以百度 token 为默认鉴权的在线代理 | 禁止作为默认 |
| 搜索等价实现 | 见 [../20260919搜索等价/](../20260919搜索等价/) |
| 前端首页 UI | 见 [../20260919前端页面/](../20260919前端页面/)（阶段一可 mock） |

---

## 4. 验收标准

1. `design.md` 含模块表（来源 docs/02）+ sync_* 映射 + Redis 聚合草图。
2. 写清 **数据进入自建存储的路径**；MCP 仅用于字段/模块形状校验。
3. `run.sh`（手工/cron）与 `mq.sh`（后期）职责差异写明。
4. `todo.md` 文档任务与「对照 MCP 再验」可执行；代码项 pending。
5. `check.md` 以 `status: in_progress` 开头。

---

## 5. 风险

| 风险 | 缓解 |
|------|------|
| 模块名/接口变更 | MCP 再验；docs/02 修订记录 |
| 同步任务把「刮对方」写成主路径 | 设计评审卡合规红线；CMS 人工/合作导入优先 |
| Redis 与 DB 不一致 | 聚合层定义 source-of-truth（建议 DB），Redis 为缓存 |
| 与前端 mock 字段漂移 | 共用合同；前端 design 链到本模块表 |

---

## 6. 依赖

- docs/02 首页模块说明
- MCP 指南（导出 home/module 等）
- 前端首页消费聚合后的自建 API 或阶段一 mock
