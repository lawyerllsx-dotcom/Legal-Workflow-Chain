# WorkBuddy 知识库强制注入 Hook 方案（核心环节）

> 实测 2026-08-07（WorkBuddy 桌面版 5.3.8）。**知识库复利的前提是"回答前先读 wiki"——靠规则自律不可靠，hook 把知识库检索变成技术强制**：每次提问自动注入知识库索引，让 AI 回答前必然看到 wiki 内容。这是复利闭环的技术底座，**不是可选增强**。
> ⚠️ **前置**：以下涉及 WorkBuddy 插件/钩子机制，改动前先备份相关 json；WorkBuddy 升级后需复测 hook.log（机制可能演进）。

## 一、为什么需要

法律 AI 工作流依赖 wiki 复利，但"回答前先读 index.md"此前只是规则约束（项目指令+用户记忆），执行强度依赖模型自律，有漏读风险。hook 把知识库检索变成硬机制。

## 二、方案选型

| 方案 | 做法 | 结果 |
|------|------|------|
| A 规则自律 | 项目指令+用户记忆 | 不满足"强制" |
| B 顶层 hooks 字段 | settings.json 顶层 `hooks`（Claude Code 同款写法）| ❌ **失败**：顶层字段被忽略 |
| C 插件机制挂 UserPromptSubmit | 市场注册+plugin.json+enabledPlugins | ✅ 成功 |

> ⚠️ **关键坑**：WorkBuddy 桌面版**不读取** settings.json 顶层 `hooks` 字段。官方文档"列出 hook 事件"与"桌面版实际生效"是两回事，必须走插件机制。**不能按 Claude Code 文档照搬。**

## 三、落地文件结构

```
~/.workbuddy/plugins/
├── known_marketplaces.json            # 市场注册表（新增 local-hooks）
└── marketplaces/
    └── local-hooks/                   # 本地市场（type=directory）
        ├── .codebuddy-plugin/
        │   └── marketplace.json       # 市场 manifest：声明插件列表
        └── plugins/
            └── wiki-inject/           # 插件本体
                ├── .codebuddy-plugin/
                │   └── plugin.json    # 插件 manifest："hooks": "./hooks/hooks.json"
                ├── hooks/
                │   └── hooks.json     # UserPromptSubmit → command
                └── scripts/
                    └── wiki-context.py # 钩子脚本（读 wiki + 输出注入 JSON + 写日志）
```

**marketplace.json**
```json
{ "name": "local-hooks", "plugins": [{ "name": "wiki-inject", "source": "./plugins/wiki-inject" }] }
```

**plugin.json**
```json
{ "name": "wiki-inject", "version": "1.0.0", "hooks": "./hooks/hooks.json" }
```

**hooks.json**（command 支持 `${CODEBUDDY_PLUGIN_ROOT}` 变量）
```json
{
  "hooks": {
    "UserPromptSubmit": [{
      "hooks": [{
        "type": "command",
        "command": "\"<python路径>\" \"${CODEBUDDY_PLUGIN_ROOT}\\scripts\\wiki-context.py\"",
        "timeout": 30
      }]
    }]
  }
}
```

**wiki-context.py** 要点（fail-open 设计）：
1. 读 `<你的vault>/wiki/index.md`
2. 提取索引 wikilink，最多带 2 个关联页面
3. 拼成上下文（上限 4000 字符：index 2000 + 每页 1500×2）
4. 输出 `{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"..."}}`
5. **任何异常返回空上下文（绝不阻断用户提问）**
6. 每次调用写日志 `~/.workbuddy/hooks/hook.log`

**注册与启用**：
- `known_marketplaces.json` 新增 `"local-hooks"`（type=directory，path 指向市场目录）
- `settings.json` → `enabledPlugins` 新增 `"wiki-inject@local-hooks": true`
- **完全重启 WorkBuddy**

## 四、验证方法（三层证据）

| 层 | 方法 | 结果 |
|---|---|---|
| 脚本单测 | 管道喂 payload，校验输出 JSON 合法、含 wiki 内容 | ✅ |
| 触发记录 | 重启后提问 → 查 `hook.log` | ✅ 出现真实记录（payload 带 session_id + transcript_path）|
| 注入实锤 | 观察提问上下文 | ✅ 用户消息后出现 `<system-reminder data-role="hook">` 含 index 全文 |

> **验证铁律：看日志而不是看回答。** 即使钩子失效，AI 也会主动读 wiki 回答，光看回答内容无法区分；日志是铁证（WorkBuddy 触发的 payload 含 session_id/transcript_path，可区分真实触发与手动测试）。

## 五、WorkBuddy vs Claude Code 机制差异

| 维度 | Claude Code | WorkBuddy 5.3.8 |
|------|------------|-----------------|
| 配置入口 | 顶层 `hooks` 字段 | **顶层字段被忽略**；必须插件机制 |
| 承载 | 直接配置即生效 | 市场注册→plugin.json→enabledPlugins |
| 事件名 | UserPromptSubmit | 相同（实测触发）|
| 输出协议 | hookSpecificOutput.additionalContext | 相同（实测注入生效）|
| 命令变量 | 无 | `${CODEBUDDY_PLUGIN_ROOT}` |
| 变更生效 | 热加载 | 完全重启 |

**结论**：事件协议同源，配置承载完全不同。WorkBuddy 用"插件化 hooks"，Claude 用"顶层字段 hooks"。任何跨平台照搬都需先实测。

## 六、维护与卸载

- **维护**：wiki 增页只需更新 `index.md`，钩子下次提问自动携带，无需改插件
- **卸载三选一**：
  1. `settings.json` → `enabledPlugins` 置 `"wiki-inject@local-hooks": false`
  2. 删 `known_marketplaces.json` 的 `local-hooks` 条目 + `marketplaces/local-hooks/` 目录
  3. 改 `hooks.json` 为空对象
- **残留**：`hook.log`（验证日志，可定期清理）

## 七、风险

| 风险 | 等级 | 对策 |
|------|------|------|
| 版本依赖 | 中 | 5.3.8 实测通过；升级后复测 hook.log |
| 全局注入 | 低 | 用户级生效，所有项目注入 wiki 索引（约 2-3k token/次）|
| 脚本故障 | 极低 | fail-open：异常输出空上下文，不影响提问 |
| token 开销 | 低 | 硬上限 4000 字符 |

> 参考：WorkBuddy 内置插件即 hooks 用例——`tencent-pptx` 的 `hooks/hooks.json`（PreToolUse 事件 + `${CODEBUDDY_PLUGIN_ROOT}`），是机制的官方参考。编码坑：Windows 下钩子脚本读 stdin payload 需显式 UTF-8 包装，否则中文路径乱码。
