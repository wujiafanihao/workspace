# baiduWiki 计划文档索引

> 本目录只放 **PLAN DOCS**（计划 / 设计 / 待办 / 验收），**不放** FastAPI / Vue / 业务源码。
> 路径（用户 Mac）：`/Users/mac/Desktop/Project/workspace/baiduWiki/plans/`

## 先读什么

| 顺序 | 文档 | 做什么 |
|------|------|--------|
| 0 | [00-js-reverse-MCP取数指南.md](./00-js-reverse-MCP取数指南.md) | 用 **js-reverse MCP**（`user-js-reverse`）观察百科类页面、抓 API、导出 JSON。**取数/验字段从这里开始。** |
| 1 | [20260919搜索等价/](./20260919搜索等价/) | 自建词条库上的**等价搜索**（UX + API 合同），默认数据来自自建存储 |
| 2 | [20260919首页同步/](./20260919首页同步/) | 首页各模块**同步进自建存储**（worker / Redis 聚合） |
| 3 | [20260919前端页面/](./20260919前端页面/) | Vue3 首页 + 搜索结果；**阶段一允许 mock，不绑真实后端** |

每个计划文件夹固定四件套（AGENTS 风格）：

- `plan.md` — 动机、目标、范围/非范围、验收、风险
- `design.md` — 技术方案（仍是文档，无实现代码）
- `todo.md` — 勾选清单（当前阶段偏规划 / 合同 / mock）
- `check.md` — 验收清单；文首必须有 `status: in_progress|complete|tests|archive`

## 与既有分析文档的关系

跨链到（已存在）：

[`../../docs/python/baiduWiki/`](../../docs/python/baiduWiki/)

约定编号（以该目录内 01–04 实际文件名为准）：

| 编号 | 用途（计划里会引用） |
|------|----------------------|
| **01** | 总览 / 背景 |
| **02** | 首页模块与接口观察（首页同步 plan/design 主依赖） |
| **03** | 搜索 API 合同与字段（搜索等价 P0 验收主依赖） |
| **04** | 补充约定 / 合规或其它专题 |

相对路径示例（从某个 plan 目录写出）：

- `../../docs/python/baiduWiki/`（目录）
- 具体文件请在该目录 `ls` 后按真实文件名链接（形如 `01-….md` … `04-….md`）

## 合规红线（全计划共用）

1. **js-reverse / 浏览器抓包**仅用于：理解交互与字段形状，设计「等价产品」。
2. **生产数据默认来自自建 CMS / DB / 自建存储**；不要把「百度 token / CDN 热刮」设计成默认生产依赖。
3. 搜索与首页同步两计划均写明：**self-built storage**；curl 裸打百科 search 常见 `code 10003`、敏感词 `1001` 等仅作观察笔记，不作为线上方案。

## 怎么让 Agent 帮你取数

直接说（示例）：

> 用 js-reverse 打开百科首页，导出 module 与 search 响应 JSON

更细的步骤与工具名见：[00-js-reverse-MCP取数指南.md](./00-js-reverse-MCP取数指南.md)

## 状态一览（创建后请改 check.md）

| 计划 | check.md status（创建时） |
|------|---------------------------|
| 搜索等价 | `in_progress` |
| 首页同步 | `in_progress` |
| 前端页面 | `in_progress` |
