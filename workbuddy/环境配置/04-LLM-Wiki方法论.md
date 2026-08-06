# LLM Wiki 方法论（Obsidian 知识库的建立方法）

> **这是作者用来建立 Obsidian 知识库的底层方法论。** 来源：开源方法论文章《LLM Wiki》（design philosophy: 设计为可直接粘贴给你的 LLM Agent 使用）。
> **给 WorkBuddy 的 AI**：用户要建 Obsidian 时，先读本文，按这套方法论引导建立——**不要只建空目录**。

## 核心思想

传统 RAG：每次查询从原始文档检索片段 → 知识没被积累，每次从头推导。

**LLM Wiki**：LLM **增量构建并维护一个持久 wiki**——结构化的、相互链接的 Markdown 集合，位于你和原始来源之间。添加新来源时，LLM 不只索引它，而是读取、提取、**整合进现有 wiki**：更新实体页、修订主题摘要、标注矛盾、强化综合结论。

> 关键：**wiki 是持久的复利资产**。交叉引用已在、矛盾已标、综合反映你读过的一切。wiki 随每个来源和每次提问越来越丰富。

## 三层架构

1. **Raw Sources** — 原始文档，不可变（LLM 只读不改），真相来源
2. **Wiki** — LLM 生成的 Markdown 页面，LLM 拥有并维护
3. **Schema（操作规范）** — 告诉 LLM 结构/约定/工作流的文件（Claude Code 用 CLAUDE.md，WorkBuddy 用 `.workbuddy/memory/MEMORY.md` + 项目指令）——让 LLM 成为有纪律的 wiki 维护者而非通用聊天机器人

## 三个操作

- **Ingest（摄入）**：丢新来源进 raw → LLM 读 → 讨论要点 → 写摘要页 → 更新 index → 更新相关实体/概念页 → 标注矛盾 → 追加 log。一个来源可能触达 10-15 个页面。
- **Query（查询）**：提问 → LLM 搜索相关页 → 阅读 → 综合回答（带引用）。**有价值的回答归档回 wiki**（不消失进聊天历史）。
- **Lint（健康检查）**：定期让 LLM 检查——矛盾、过期声明、孤立页、缺概念页、缺交叉引用、数据缺口。

## 两个特殊文件

- **index.md**（内容导向）：wiki 的目录——每页一行（链接 + 一句话摘要 + 元数据），按类组织。LLM 每次摄入更新它。回答问题时**先读 index 定位**，再深入。
- **log.md**（时间导向）：追加式操作记录（`## [日期] ingest | 标题` 前缀格式）。给出 wiki 演化时间线。

## 给 WorkBuddy 的建立指引

1. 用户说"建知识库" → 先读本文 + 参考 `01-Obsidian知识库搭建.md` 的目录结构
2. **先建 index.md**（空骨架，说明分类），再建 log.md
3. 建好 `wiki/{checklists,concepts,entities,sources,synthesis,sessions}` + `raw/`
4. 告诉用户用法三招：**"收进知识库"（Ingest）/ 直接提问（Query）/ "检查知识库"（Lint）**
5. 强调：**先读 index 再回答**（防止 wiki 里有却视而不见）；有价值的分析归档回 synthesis

## 来源

- 英文原文《LLM Wiki》：A pattern for building personal knowledge bases using LLMs（可直接复制给任何 LLM Agent 的开源方法论文档）
- 中文提炼：本文件

## 许可

LLM Wiki 方法论为开源文章，可自由分享用于个人知识库搭建。
