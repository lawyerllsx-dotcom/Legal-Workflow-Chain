# 来源与致谢

> 本项目整合了多个开源法律 AI 技能库，经本地化整合、修改、测试后形成。**尊重每一位原作者，这里郑重致谢。**

## Skill 来源对照

| 本项目 Skill | 来源 | 作者 | 许可 | 分发状态 |
|-------------|------|------|------|---------|
| `deductive-reasoning` | [THUYRan/Legal-Skills-Chinese](https://github.com/THUYRan/Legal-Skills-Chinese) | 胡伊然等 12 位执业法律专业人员 | CC BY-NC-ND 4.0 | 未随仓库分发 |
| `dispute-issue-identification` | 同上 | 同上 | CC BY-NC-ND 4.0 | 未随仓库分发 |
| `conflict-resolution` | 同上 | 同上 | CC BY-NC-ND 4.0 | 未随仓库分发 |
| `legal-research` | [Golden2002/legal-research-skill](https://github.com/Golden2002/legal-research-skill) | Golden2002 | MIT | 随仓库分发 |
| `legal-fact-checker` | [NEU-ZHA/legal-ai-skills](https://github.com/NEU-ZHA/legal-ai-skills) | NEU-ZHA | 见原仓库 | 随仓库分发 |
| `legal-citation-comprehensive` | 同上 | 同上 | 见原仓库 | 随仓库分发 |
| `evidence-catalog-generator` | 同上 | 同上 | 见原仓库 | 随仓库分发 |
| `docx-editing` | 同上 | 同上 | 见原仓库 | 随仓库分发 |
| `接案评估` | [fayayy888/legal-document-assistant](https://github.com/fayayy888/legal-document-assistant)(十步骨架) | fayayy888 | 见原仓库 | 随仓库分发 |
| `vision` | [xiincs/claude-code-vision-skill](https://github.com/xiincs/claude-code-vision-skill) | xiincs | 见原仓库 | 随仓库分发 |

## 致谢

- **THUYRan** 及其 12 位作者——贡献了法律推理三件套（演绎 / 争点 / 竞合），是这套体系推理层的核心。原库 38 个技能、SKILL.md 标准化、评测基准覆盖，都是专业水准的示范。
- **Golden2002**——法律检索 skill 的检索方法论（效力层级、五步法、身份分层），本项目的 legal-research 建立在其上。
- **NEU-ZHA**——占位符防编造模式、引注核验、DOCX 处理思路，fact-checker 与 citation 从中受益。
- **fayayy888**——接案评估的十步骨架，启发了本项目的接案入口设计。
- **xiincs**——vision skill 的路由架构，本项目用它做视觉识别。

## 整合说明

本项目不是简单搬运：每个 skill 都经过**本地化整合**（加入接力协议、结构化上下文、与 MCP 的配合、回归测试），再叠加本工作流独有的部分（可选深链、接案评估双模式、运行日志进化）。

## ⚠️ 许可声明（重要）

- `deductive-reasoning` / `dispute-issue-identification` / `conflict-resolution` 源自 **CC BY-NC-ND 4.0** 项目。该许可**禁止衍生修改后再分发**。因此这三个 skill **未随本仓库分发**——仅保留在作者本地自用（个人自用不构成分发），需要落地 skill 时请按 [推理层接入指南](推理层-接入指南.md) 从 [THUYRan 原库](https://github.com/THUYRan/Legal-Skills-Chinese) 下载原版并本地接线（个人非商用）。其方法论文档见 [五层架构](五层架构.md)。
- 其余 skill 的来源许可，请以各原仓库为准；如原仓库要求保留版权声明，请在使用时一并保留。
- 本项目作者对整合方式已尽力尊重原作者的署名与许可，若原作者认为整合方式不妥，可联系移除。

---

*尊重每一份开源贡献。方法无边界，署名有温度。*
