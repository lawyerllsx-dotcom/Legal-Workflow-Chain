# 环境配置 · 03 — 模型与 API Key 获取

> 给 WorkBuddy 的 AI 当引导剧本。**凡涉及 key：停下，指导用户自己填（界面或配置文件），不要接收用户粘贴的 key。** key 只存在于用户本机配置文件，不进入对话/日志。所有 key 都是用户（朋友）自己注册持有，迁移包不含任何 key。

## 一、模型 Key（必填）

WorkBuddy 需接大模型干活。**只需配 DeepSeek**（日常主力，便宜，纯文本推理够用）：

| 服务 | 注册 | Key 在哪 | 建议模型 |
|------|------|---------|---------|
| **DeepSeek** | platform.deepseek.com | API Keys 页 | `deepseek-v4-pro` / `deepseek-v4-flash` |

**在 WorkBuddy 里配置**，二选一：
- **界面**：设置 → 模型 → 添加模型，填 `base URL + API key + 模型 id`
- **配置文件**：把 `models.json` 复制到 `~/.codebuddy/models.json` 或 `~/.workbuddy/models.json`（按你的版本），填上 key。官方结构为 `models` 数组：
  - DeepSeek：`url=https://api.deepseek.com/v1`，`id=deepseek-v4-pro` / `deepseek-v4-flash`

> 💡 **GLM 无需配置**：WorkBuddy **内置 GLM**（模型列表直接有），传图时切内置 GLM 识别即可，识别完切回 DeepSeek 继续（上下文不变）。
> ⚠️ 配置 url 必须写完整地址（含 `/v1` 路径），不能只写域名。

## 二、法条/案例检索 Key（推荐配）

| 服务 | 注册 | 用途 |
|------|------|------|
| **元典开放平台** | open.chineselaw.com | 中国法条语义检索、案例详情、企业涉诉（核心检索源）|

配好后，把 key 填进 `mcp.json` 的 `Authorization: Bearer` 字段。

## 三、联网搜索（无需配置）

> ✅ **实测 2026-08-07**：WorkBuddy **内置联网搜索**，无需 tavily、无需任何 key。问最新信息（新闻/行情/时事）直接实时联网。法条检索走元典（核心源），联网用于兜底/时效信息。

## 四、配置检查清单

- [ ] 模型 key 填好，WorkBuddy 能正常对话
- [ ] 元典 key 填好（`mcp.json`），问一个法条能返回原文
- [ ] 联网搜索：问"今天有什么新闻"能实时返回（内置，无需配）

> 安全提示：key 只填在你本机的配置文件里，**别发到任何群聊或公开仓库**。
