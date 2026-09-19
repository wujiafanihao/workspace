# 设计：首页同步（20260919）

> 无业务源码。模块清单以 [`docs/02`](../../../docs/python/baiduWiki/) 为准，下表为设计骨架，**请用 MCP 再验后改「观察路径」列。**

---

## 1. 总览

```text
                    ┌─────────────┐
  运营/CMS/导入 ──► │ 自建存储 DB  │ ◄── sync_* workers（写）
                    └──────┬──────┘
                           │ 构建/刷新
                    ┌──────▼──────┐
                    │ Redis 聚合   │  （首页读模型，可 P1）
                    └──────┬──────┘
                           │ GET /api/home（后续）
                    ┌──────▼──────┐
                    │ 前端首页     │  （阶段一可 mock）
                    └─────────────┘
```

**观察用**：js-reverse 看 `/lemma/api/home/module|statistic|dynamic`、CDN JSON。  
**生产用**：自建表 + sync_* +（可选）Redis。不把百度 CDN/token 当默认依赖。

---

## 2. 模块表（对齐 docs/02）

> 「观察路径」来自既往笔记，**非生产 URL 依赖**。

| module_key | 展示含义（白话） | 观察路径（参考） | 自建表/集合（建议名） | sync 工人 |
|------------|------------------|------------------|------------------------|-----------|
| `module` | 首页主模块拼装 | `/lemma/api/home/module` | `home_module` | `sync_home_module` |
| `statistic` | 统计数字/概况 | `/lemma/api/home/statistic` | `home_statistic` | `sync_home_statistic` |
| `dynamic` | 动态流 | `/lemma/api/home/dynamic` | `home_dynamic` | `sync_home_dynamic` |
| `hot_lemmas` | 热词 | CDN `hotLemmas.json` | `home_hot_lemmas` | `sync_hot_lemmas` |
| `events_on_history` | 历史上的今天 | CDN `eventsOnHistory/MM.json` | `home_events_on_history` | `sync_events_on_history` |

补充列（落地时加）：更新频率、负责人、是否允许人工在 CMS 覆盖。

若 docs/02 还有其它模块：按同样行格式追加，勿删表头。

---

## 3. sync_* workers

### 3.1 职责

每个 `sync_*`：

1. **输入**：自建源（CMS 导出、合作方包、内部 API）——**默认不是**线上百度。
2. **变换**：映射到自建 schema（字段对齐观察形状，便于前端等价 UX）。
3. **写入**：对应表；写版本号 / `updated_at`。
4. **可选**：成功后刷新 Redis 聚合键。

### 3.2 开发期「对照观察」

允许开发机用 MCP **导出一份样例 JSON**，放进 `fixtures/`（脱敏），供：

- schema 评审
- 前端 mock
- 单测金样

**禁止**：把「定时 curl 百度 + token」写进默认 `run.sh` 而无合规评审。

### 3.3 命名

```text
sync_home_module
sync_home_statistic
sync_home_dynamic
sync_hot_lemmas
sync_events_on_history
```

共享库（后期）：`sync_common`（日志、重试、分布式锁）。

---

## 4. Redis 聚合

### 4.1 建议键

| Key | 类型 | 含义 |
|-----|------|------|
| `home:aggregate:v1` | String(JSON) 或 Hash | 首页一次拉取的聚合包 |
| `home:module:{key}:v1` | String(JSON) | 单模块缓存（可选） |

### 4.2 聚合 JSON 草图

```json
{
  "version": 1,
  "updated_at": "ISO-8601",
  "modules": {
    "module": {},
    "statistic": {},
    "dynamic": {},
    "hot_lemmas": {},
    "events_on_history": {}
  }
}
```

### 4.3 失效

- 任一 sync_* 成功 → 重算聚合或 DEL `home:aggregate:v1`
- TTL 保底（如 5–30 min），防止永久脏读

P0 可「API 直读 DB」；Redis 标 P1。

---

## 5. run.sh vs mq.sh

| | `run.sh`（先做） | `mq.sh`（后期） |
|--|------------------|-----------------|
| 触发 | 人工 / crontab | 消息队列消费 |
| 适用 | 模块少、频率低、先跑通 | 多模块、需重试/削峰 |
| 内容（文档约定） | 依次或并行调用各 sync_*；最后 refresh 聚合 | 订阅 `home.sync.*`；失败进死信 |
| 配置 | env 文件：DB/Redis DSN | 另加 MQ endpoint |

本阶段只要求：**在 design/todo 写清脚本职责**；脚本文件本身可 pending（若补文档示例，勿夹带真实密钥）。

---

## 6. 读出 API（后续，非本阶段实现）

草图：`GET /api/home` → 读 Redis 聚合，miss 则读 DB 并回填。  
前端阶段一可不调此 API，改用 mock（见前端计划）。

---

## 7. 合规复核表

| 检查项 | 期望 |
|--------|------|
| Source of truth | 自建 DB/CMS |
| 百度 token | 非生产默认 |
| CDN 热刮 | 非生产默认 |
| MCP | 仅观察与 fixtures |

---

## 8. 与搜索/前端

- 热词点击可跳搜索页：`/search?word=`，合同见搜索计划。
- 前端 mock 的 `home` fixture 应与本聚合 `modules` 键一致。
