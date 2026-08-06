# 环境配置 · 03 — 模型与 API Key 获取

> 给 WorkBuddy 的 AI 当引导剧本。**凡涉及 key：停下询问用户本人，由用户注册并填入，绝不猜测或自动填。** 所有 key 都是用户（朋友）自己注册持有，迁移包不含任何 key。

## 一、模型 Key（必填）

WorkBuddy 需要接一个大模型才能干活。二选一（或都配）：

| 服务 | 注册 | Key 在哪 | 建议模型 |
|------|------|---------|---------|
| **DeepSeek**（推荐，便宜）| platform.deepseek.com | API Keys 页 | `deepseek-v4-pro` / `deepseek-v4-flash` |
| **智谱 GLM** | bigmodel.cn | API 密钥页 | `glm-4.6` |

**在 WorkBuddy 里配置**，二选一：
- **界面**：设置 → 模型 → 添加模型，填 `base URL + API key + 模型 id`
- **配置文件**：把 `models.json` 复制到 `~/.codebuddy/models.json` 或 `~/.workbuddy/models.json`（按你的版本），填上 key。官方结构为 `models` 数组：
  - DeepSeek：`url=https://api.deepseek.com/v1`，`id=deepseek-v4-pro` / `deepseek-v4-flash`
  - 智谱 GLM：`url=https://open.bigmodel.cn/api/paas/v4`，`id=glm-4.6`

## 二、法条/案例检索 Key（推荐配）

| 服务 | 注册 | 用途 |
|------|------|------|
| **元典开放平台** | open.chineselaw.com | 中国法条语义检索、案例详情、企业涉诉（核心检索源）|

配好后，把 key 填进 `mcp.json` 的 `Authorization: Bearer` 字段。

## 三、联网兜底 Key（可选）

| 服务 | 注册 | 用途 |
|------|------|------|
| **tavily** | tavily.com | 联网搜索兜底（免费 1000 次/月）。元典断额/查不到时降级用 |

配好后填进 `mcp.json` 的 tavily url 里。

## 四、配置检查清单

- [ ] 模型 key 填好，WorkBuddy 能正常对话
- [ ] 元典 key 填好（`mcp.json`），问一个法条能返回原文
- [ ] tavily 可选，填了联网更稳

> 安全提示：key 只填在你本机的配置文件里，**别发到任何群聊或公开仓库**。
