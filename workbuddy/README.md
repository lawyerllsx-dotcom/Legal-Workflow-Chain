# WorkBuddy 迁移方案（初版）

> 把 Legal-Workflow-Chain 法律 AI 工作流适配到 **腾讯 WorkBuddy**（桌面 agent，低门槛，无需装 VS Code + Claude Code）。
> 供想用 WorkBuddy 而非 Claude Code 的朋友/同事使用。

## 这是什么

一份「WorkBuddy 引导式搭建」方案：把 WorkBuddy 当安装导师，自动解析本目录文件，按阶段 A-G 一步步引导装好（模型 → 技能 → 编排 → MCP → Obsidian → OCR），做到**几乎同步作者的工作流环境**。

## 目录

| 文件 | 用途 |
|------|------|
| [WORKBUDDY.md](WORKBUDDY.md) | **编排规则**（路由裁决/复杂度三问/F1-F5/接案评估触发）——粘贴到项目「指令」字段或存为 `.workbuddy/memory/MEMORY.md` |
| [部署说明.md](部署说明.md) | 技能怎么装到 WorkBuddy |
| [安装说明.md](安装说明.md) | WorkBuddy 引导式搭建剧本（阶段 A-G）|
| [使用手册.md](使用手册.md) | 新手上手 + 工作流用法 |
| [测试与排查指南.md](测试与排查指南.md) | 装完逐项测试 + 反馈表 |
| [mcp.json](mcp.json) / [models.json](models.json) | 配置模板（填你自己的 key）|
| [环境配置/](环境配置/) | Obsidian 知识库 / 本地 OCR / 模型与 Key 三份搭建文档 |

## 与主仓库的关系

- 主仓库 `skills/`（7 个公开 skill）可直接部署到 WorkBuddy（SKILL.md 是 OpenClaw/WorkBuddy 同规范）。
- **本板块 `workbuddy/skills/` 共 8 个适配版 skill**（description 已为 WorkBuddy 触发钩子优化），`docs/` 另有 7 个 Claude Code 版。
- **推理层 3 个 skill**（争点识别/演绎/竞合）因来源许可（CC BY-NC-ND）**未随仓库分发**——WorkBuddy 版按 [推理层接入指南](../docs/推理层-接入指南.md) 自取原版并本地接线。**WorkBuddy 适配三步（description 触发钩子 / 编排层载体 / 总览衔接）见该指南 [四·B 节](../docs/推理层-接入指南.md#四bworkbuddy-用户的适配用-workbuddy-而非-claude-code-时)。**
- 本地 OCR 工具（PP-OCRv6 脚本）为作者私有，不在此公开——需要的朋友从作者处索取。

## 关键机制（官方确认）

- **编排层载体**：WorkBuddy 项目配置的「指令」字段 = 对 AI 的全局行为规则，**所有任务自动继承**（官方文档确认）。
- **技能安装**：WorkBuddy 技能管理 → 添加技能 → **上传技能**（官方方式）。
- **记忆**：`.workbuddy/memory/MEMORY.md` 会注入上下文（个人记忆）。

## 许可与说明

- 本方案文档为 MIT（随主仓库）。**不含任何 API key、案件数据**。
- 推理层 3 个 skill 非商用自用，**请勿再向外转发**。
- 每份 AI 产出都是草稿，由执业律师复核后再使用。

## 状态

**初版**，正在真实环境测试中（见 [测试与排查指南.md](测试与排查指南.md) 反馈表）。版本差异可能导致个别步骤需微调，欢迎反馈。
