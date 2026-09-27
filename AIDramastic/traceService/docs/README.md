# traceService/docs — 文档索引

| 文件 | 用途 |
|------|------|
| [`PRD.md`](PRD.md) | 产品需求：背景、故事、FR/NFR、schema、验收 |
| [`DESIGN.md`](DESIGN.md) | 详细设计：模块、API 示例、DDL、配置、双 Worker |
| [`ARCHITECTURE.md`](ARCHITECTURE.md) | 架构：C4、序列、失败模式、并发峰值 |
| [`PLAN.md`](PLAN.md) | 开发计划（含 Python Worker Task + Go Worker Task） |
| [`TODO.md`](TODO.md) | 执行细清单 |

**架构一句话**：**FastAPI API + Python Worker + Go Worker + Redis + SQLite**（两级队列）；主业务库 MySQL 不混用。
