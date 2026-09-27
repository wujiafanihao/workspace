# azyasaxi 专属工作空间

这是 **azyasaxi** 的专属开发工作空间，用来编写和迭代各类服务与工具。

## 适合做什么

- 各类后端 / 业务服务
- **Go** 项目与微服务
- **Python** 脚本、服务与工具
- **Java**（含 Kotlin / JVM）服务

## 目录约定（起步）

| 路径 | 说明 |
| --- | --- |
| `docs/` | 文档、说明与笔记 |
| `AGENTS.md` | Agent / 协作约定（按需填写） |
| `.gitignore` | 已覆盖 Go / Python / Java 等常用忽略项 |

按语言或服务建子目录即可，例如 `services/`、`go/`、`python/`、`java/`，没有强制结构。

## Git 分支与协作约定（硬性）

### 总原则：一功能一分支

**一个需求 = 一条特性分支**，分支名 `feat/<年月日>-<需求名>`（与 `plans/<年月日><需求名>/` 同名同义）。
不在一条分支上堆多个需求，不在别人分支上开发，需求完成即合入并归档。

### 分支职责

| 分支 | 谁维护 | 能做什么 | 禁止做什么 |
| --- | --- | --- | --- |
| `main` | 全员基线 | 承载「已完成并自检到 `archive` 的需求」；工作空间级文档/协议改动可直接写并 push | 直接在 `main` 上开发功能代码 |
| `AIDramastic` | **jiafawu** 创建并维护 | 仅由 owner 合入；他人只能通过 **MR** 请求合入 | **禁止任何其他人把自己的 `feat/*` 合入该分支，禁止直接 push** |
| `feat/<年月日>-<需求名>` | 该需求的开发者本人 | 开发、自测、push 到远程同名分支 | 混装多个需求；并入他人特性分支 |

### 权限规则（谁能点「合并」）

按**分支归属**定权，不按仓库定权：

| 分支 | 谁能提 MR | 谁能执行合并 |
| --- | --- | --- |
| jiafawu 创建的分支（`main`、`AIDramastic` 等） | 任何人 | **仅 jiafawu**（提 MR、合并、push 全权限） |
| 他人创建的远程分支（`feat/<年月日>-<需求名>`） | 任何人 | **创建者本人 + jiafawu** |

一句话：**合并权 = 分支创建者 ∪ jiafawu；其余人只能提 MR，不能点合并。**
仓库 `.github/CODEOWNERS` 为 `* @wujiafanihao`，所有改动均需 jiafawu review 后由其合并。

### 关键规则（重点）

1. **可以基于某个特定远程分支新建自己的分支**（基线由需求决定，默认 `origin/main`）：

   ```bash
   git fetch origin
   # 默认：基于远程 main 切
   git checkout -b feat/20260927-xxx origin/main
   # 需要 AIDramastic 上的基线时：基于远程 AIDramastic 切（只是"起点"，不是"归属"）
   git checkout -b feat/20260927-xxx origin/AIDramastic
   git push -u origin feat/20260927-xxx
   ```

2. **自己的 feat 只往自己的特性分支合**，即自集成、自闭环；**绝不合入 jiafawu 创建的 `AIDramastic` 分支**。
   需要 `AIDramastic` 上的代码时，走「基于它新建分支」或「提 MR」，不要反向 merge 进去。

3. **工作空间级改动（文档、协议、脚本等）在 `main` 上写，然后 push 远程**：

   ```bash
   git checkout main && git pull --ff-only origin main
   # 改动 → 提交 → git push origin main
   ```

4. **需要落到 `AIDramastic` 的内容，向本地 `AIDramastic` 分支提 MR**（target = `AIDramastic`，source = `main` 或自己的 `feat/*`），
   由分支 owner 评审后合入；未评审通过不得自行 merge。

### 一功能一分支标准流程

```text
git fetch origin
  → 基于指定远程分支切 feat/<年月日>-<需求名>
  → 建 plans/<年月日><需求名>/{plan,design,todo,check}.md（status=in_progress）
  → 在特性分支上开发 + 测试，push 到 origin/feat/...
  → check.md 走到 archive（自检 + 测试通过）
  → 合入 main 并 push 远程
  → 向本地 AIDramastic 提 MR（如需落到该分支）
```

## 说明

本地密钥、虚拟环境、构建产物等已由 `.gitignore` 忽略，勿把 `.env`、密钥和依赖目录提交进仓库。
