# 环境配置 · 01 — Obsidian 知识库搭建

> 给 WorkBuddy 的 AI 当引导剧本用，也给人照着做。目标：搭出和你工作目录配套的知识库（wiki），让 skill 用起来有沉淀。

## 一、装 Obsidian

1. 官网下载：[obsidian.md](https://obsidian.md) → 选 Windows 版
2. 安装后新建 **Vault（库）**：
   - 点 "Open folder as vault" / 新建
   - 选一个本地文件夹作为库（建议建一个专用文件夹，如 `D:\LegalWiki` 或文档里的 `我的法律工作`）

> 这个 vault 文件夹就是你的**工作目录**。WorkBuddy 打开它干活，WORKBUDDY.md 也放这里。

## 二、建 wiki 目录结构

在 vault 根目录建以下子文件夹（对应知识分类）：

```
<你的vault>/
├── .workbuddy/           # 配置（含 memory/MEMORY.md 编排规则，从迁移包复制）
├── raw/                  # 原始材料（PDF、文章、案卷），只读不修改
└── wiki/                 # 知识库（AI 生成和维护）
    ├── index.md          # 索引页（最重要，先建）
    ├── log.md            # 操作日志
    ├── overview.md       # 总览
    ├── checklists/       # 实务速查表
    ├── concepts/         # 概念、方法论
    ├── entities/         # 人物、组织、案件
    ├── sources/          # 原始文档摘要
    ├── synthesis/        # 综合分析、跨页面梳理
    └── sessions/         # 会话归档（可选）
```

## 三、放规则文件

把迁移包里的 **`.workbuddy/`** 文件夹复制到 vault 根目录——里面的 `.workbuddy/memory/MEMORY.md` 是 WorkBuddy 自动加载的编排规则（驱动路由裁决 / 复杂度三问 / F1-F5 / 接案评估自动触发）。

## 四、按操作规范建立（关键）

**不要只建空目录**——让 WorkBuddy 按《Wiki 操作规范》建立（和作者一致），先读 `05-Wiki操作规范.md`（可执行规范）+ `04-LLM-Wiki方法论.md`（底层思想）：

1. 在 WorkBuddy 打开 vault，说：
   > "读 `环境配置/05-Wiki操作规范.md` 和 `环境配置/04-LLM-Wiki方法论.md`，按这套规范帮我建知识库：先建 index.md 和 log.md，建好 wiki 分类（concepts/entities/sources/synthesis/checklists/sessions）+ raw/，然后我往里放资料，你按 Ingest 逐步摄入并维护"
2. 建好后，三操作和作者完全一致：

| 操作 | 你说 | AI 做 |
|------|------|-------|
| **Ingest** | "把这个材料收进知识库" | 读源 → 汇报要点 → 写来源摘要页（数据标页码）→ 更新概念/实体页 → 完善法条 → **标矛盾** → 更新索引 → 追加日志 |
| **Query** | 直接问法律问题 | **先读 index 定位** → 深入 → 综合回答 → 判断收纳价值 |
| **Lint** | "检查一下知识库" | 断链/孤立页/矛盾/过期/索引一致性 → 出报告 |

3. **核心纪律**（务必传达给 AI，和作者一致）：
   - **先读 index 再回答**（防止 wiki 里有却视而不见）
   - 矛盾主动标注（`> ⚠️ 矛盾:`）
   - 有价值的分析**收纳回 synthesis**，不消失进聊天
   - `raw/` 只读不修改；来源摘要数据标注页码

## 五、为什么值得搭

知识库是**复利资产**：今天查的法条、整理的案例、提炼的方法，以后直接调出来用，不用重新查。skill 管"今天怎么干活"，wiki 让"明天比今天更厉害"。

> 初始是空的没关系——从第一个案件材料开始，慢慢攒。这正是"几乎同步"知识库环境的意义：结构一样，内容自己长。
