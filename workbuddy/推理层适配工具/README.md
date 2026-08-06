# 推理层 skill WorkBuddy 适配工具

把 THUYRan **原版** 推理层 3 个 skill（`dispute-issue-identification` / `deductive-reasoning` / `conflict-resolution`）一键适配为 **WorkBuddy 可触发版本**，在你本机完成，不产生任何对外分发（符合 CC BY-NC-ND 的个人自用条款）。

## 为什么需要它

原版 SKILL.md 的 `description` 面向 Claude Code 工作流，WorkBuddy 的模型**靠 description 主动匹配调用技能**——原版格式不优化，WorkBuddy 就不会自动触发这 3 个 skill。本脚本只替换 `description` 为触发钩子格式，正文一律不动。

## 用法

```bash
# 1. 下载原版（个人非商用）
git clone https://github.com/THUYRan/Legal-Skills-Chinese.git

# 2. 适配全部 3 个推理层 skill
python adapt_for_workbuddy.py --all Legal-Skills-Chinese/skills

# 也可以逐个指定
python adapt_for_workbuddy.py Legal-Skills-Chinese/skills/deductive-reasoning
```

## 效果

对每个 skill：

| 文件 | 说明 |
|------|------|
| `SKILL.md` | 已适配——`description` 改为触发钩子格式（WorkBuddy 可识别）|
| `SKILL.md.original` | 原版备份（恢复：`cp SKILL.md.original SKILL.md`）|

重复运行安全（已适配会自动跳过）。

## 适配后

把三个 `SKILL.md` 上传到 WorkBuddy（**技能管理 → 添加技能 → 上传技能**），并配好编排规则（项目「指令」字段 或 `.workbuddy/memory/MEMORY.md`）——这样深链（评估 → 争点 → 检索 → 推理 → 核查 → 输出）才能在 WorkBuddy 里自动流转。详见 [推理层接入指南](../../docs/推理层-接入指南.md) 四·B 节。

> 合规说明：本脚本不包含原版 skill 的任何内容，仅提供我们的原创触发钩子描述。你在本机修改自己下载的原版副本，属 CC BY-NC-ND 允许的「个人下载、自行修改、本地自用」。改编版**不得再对外分发**。
