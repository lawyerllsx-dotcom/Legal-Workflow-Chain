# Wiki 知识库搭建

> Legal-Workflow-Chain 的 skill 负责"做分析"，CLAUDE.md 负责"管流程"，**wiki 负责"攒知识"**。三者一起用才是完整工作台。

## 为什么需要 wiki

每次让 Claude 查法条、写文书、做案件分析——如果不存下来，下次还得从零查、从零写。**wiki 是"知识复利"的载体**：今天检索的案例、提取的方法、上级教的套路，以后直接调出来复用。

这是 Legal-Workflow-Chain 和单纯"装几个 skill"拉开差距的地方：**skill 管今天怎么干，wiki 让明天比今天更厉害。**

## 三层架构

```
CLAUDE.md  （操作用指南——告诉 Claude 怎么管 wiki）
    ↓
wiki/      （知识层——Claude 生成和维护，按分类组织）
    ├── concepts/   概念、方法论、术语
    ├── entities/   人物、组织、案件
    ├── sources/    原始文档的摘要
    ├── synthesis/  综合分析、跨页面梳理
    ├── sessions/   会话归档（可选）
    └── checklists/ 实务速查表
    ↓
raw/       （原始来源——PDF、文章、案卷材料，只读不修改）
```

## 从零搭建（三步）

### 第一步：建 Obsidian Vault

装好 [Obsidian](https://obsidian.md)，新建 Vault → 选一个本地文件夹（如 `LegalWiki`）。

### 第二步：放 CLAUDE.md 和建目录

把仓库根部的 `CLAUDE.md` 复制到 Vault 根目录，然后建好子目录：

```bash
cd /你的/obsidian/vault/
cp /path/to/Legal-Workflow-Chain/CLAUDE.md .
mkdir -p wiki/{concepts,entities,sources,synthesis,sessions,checklists}
mkdir raw
```

### 第三步：开始用

在 Vault 里用 Claude Code 打开，说：

```
帮我用这个知识库，先建个索引页 wiki/index.md。
然后我开始往里放资料，你帮我分类、建页面、做交叉引用。
```

**核心用法就三招**：

| 你说 | Claude 做 |
|------|-----------|
| "ingest / 把这个加到知识库" | 读材料 → 写摘要页 → 更新概念页 → 标矛盾 → 更新索引 |
| 直接提问（合同纠纷怎么办/这个案怎么打）| 先查 wiki，wiki 有的引用 wiki，没有的用外部工具补充 |
| "lint / 检查一下" | 查断链、孤立页、过期声明、法条时效性——出报告 |

> ⚠️ 别跳过第 0 步：**回答任何问题时，Claude 必须先读 wiki/index.md 定位相关内容**——这是 CLAUDE.md 的铁律，防止"wiki 里明明有但 Claude 视而不见"。

## wiki 和 Legal-Workflow-Chain skill 的关系

```
wiki（知识资产）  ←→  CLAUDE.md（操作规范）  ←→  skill（执行引擎）
   "沉淀下来的东西"        "每一步该怎么做"          "真的去做分析/写文书"
```

- skill 写文书时引用 wiki 里的上级方法论、类案模板
- wiki 里查下来的法条时效性由 lint 流程定期核查
- 接案评估产出的报告可以收纳成 synthesis 页复用

没有 wiki 也能用 skill（它们是独立可跑的），但**有 wiki 才有复利**——每做一件事，知识资产跟着涨。

## 会话归档（进阶）

Claude Code 的对话记录（transcripts）可以归档到 `wiki/sessions/`，按案件分组保存结构化摘要。不是必须的，但如果想**回溯某个案子的推理过程和决策节点**，这套机制就在那里。

## 相关

- [README](../README.md) — Legal-Workflow-Chain 项目总览
- [五层架构](五层架构.md) — Skill 组织 / 接力 / 路由裁决
- [接案评估](接案评估.md) — 接案入口 + 双模式
