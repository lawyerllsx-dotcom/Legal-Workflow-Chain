---
name: vision
description: |
  当用户需要【视觉识别（识人/识物/识场景/图表/UI）】时使用。触发词：识别这是谁、看图、视觉识别、图片内容。
  输出：图片内容的文字描述。不做：文字内容识别（文档/票据文字走 OCR，不用本技能）。
---

# vision

Multi-provider vision tool. Call various vision models to describe images. Feed it a prompt + image path, get back a text description.

## ⚠️ 使用边界：文字内容一律走 OCR，不要用本工具

本工具是**视觉理解**（识人、识物、识场景、看图说话），**不是 OCR**。

- **文字内容**（文档、证据、票据、合同页、截图里的文字等）→ **用 OCR 提取文字，不要调用本工具**：
  - 本地 OCR（默认优先，不联网）：使用本机已安装的 OCR 工具（如 PaddleOCR 本地版、ocrmypdf 等），或平台内置的 OCR 能力
  - 线上 OCR（须经用户明确同意）：`mcp__paddleocr__*`
- **非文字内容**（识别人物/物体/场景/图表/UI 布局等）→ 用本工具。
- **触发条件**：仅在**用户明确要求视觉识别**（"识别这是谁""看看这张图""用视觉识别"）或内容明显为非文字时调用。**用户未指明时，默认按文字内容处理、走 OCR。**

聊天中粘贴的图片：先提取到临时文件，按上述规则路由——文字内容 → 本地 OCR；非文字/用户指明 → 本工具。

## When to use this tool

If you can already see and understand the image yourself (native multimodal model), skip this tool — analyze it directly.

A SessionStart hook normally announces this session's routing status up front. If that context isn't visible (e.g. compacted out of a long conversation, or the hook isn't installed), check before calling this tool:

```bash
python vision.py --check-routing
```

- `native` → you already have native image understanding this session; don't call this tool.
- `external` (default) → proceed with the quick start below.

## Quick start

```bash
python vision.py [--provider <name>] <image_path> <prompt>
```

When `--provider` is omitted, the provider is resolved by: `--provider` flag > `VISION_PROVIDER` env > first API key found.

## Providers

### doubao (Volcengine Ark)

- API key: `DOUBAO_API_KEY`
- Default model: `doubao-seed-2-0-pro-260215`
- Custom endpoint: `DOUBAO_BASE_URL`

### qwen (DashScope)

- API key: `DASHSCOPE_API_KEY`
- Default model: `qwen-vl-max`
- Custom endpoint: `DASHSCOPE_BASE_URL`
- Available models: `qwen-vl-max`, `qwen-vl-plus`, `qvq-max`

### openai (GPT-4o)

- API key: `OPENAI_API_KEY`
- Default model: `gpt-4o`
- Custom endpoint: `OPENAI_BASE_URL`
- Also works with any OpenAI-compatible endpoint.

### anthropic (Claude)

- API key: `ANTHROPIC_API_KEY`
- Default model: `claude-sonnet-5`
- Custom endpoint: `ANTHROPIC_BASE_URL`
- Requires the `anthropic` package (`pip install anthropic`); it's imported lazily so other providers work without it.

### any custom provider

Any `--provider` name outside the built-in four is resolved dynamically from
environment variables named after it — no code changes needed:

| Env Var | Required | Notes |
|---------|----------|-------|
| `{NAME}_API_KEY` | yes | checked at request time, same as built-ins |
| `{NAME}_BASE_URL` | yes | no default — arbitrary endpoint |
| `{NAME}_MODEL` | yes | no default (or set global `VISION_MODEL` instead) |
| `{NAME}_PROTOCOL` | no | `openai` (default) or `anthropic` — picks the request shape |

`openai` covers essentially every OpenAI-compatible endpoint (vLLM, Ollama,
LiteLLM, OpenRouter, Azure OpenAI, self-hosted proxies, ...). Use
`{NAME}_PROTOCOL=anthropic` only if the endpoint speaks the Anthropic Messages
API shape.

```bash
export MYAPI_API_KEY="sk-xxx"
export MYAPI_BASE_URL="https://my-endpoint.example.com/v1"
export MYAPI_MODEL="my-vision-model"
python vision.py --provider myapi "screenshot.png" "describe this"
```

If `{NAME}_BASE_URL` or `{NAME}_MODEL` is missing, the tool prints exactly which
variables to set instead of a generic "unknown provider" error.

## Configuration

| Env Var | Scope | Default |
|----------|-------|---------|
| `VISION_PROVIDER` | Default provider (built-in or custom name) | auto-detect (built-ins only) |
| `VISION_MODEL` | Override model (all providers) | provider default |
| `{PROVIDER}_MODEL` | Override model (per provider) | — |
| `{PROVIDER}_BASE_URL` | Override/define endpoint (per provider) | built-in default, or required for custom |
| `{PROVIDER}_PROTOCOL` | Request shape for a custom provider: `openai` \| `anthropic` | `openai` |
| `VISION_TEMPERATURE` | Response creativity 0–1 | `0` |
| `VISION_MAX_TOKENS` | Max response tokens | `4096` |

Note: auto-detect (no `--provider` / `VISION_PROVIDER` set) only scans the four
built-in providers' API keys — a custom provider must always be named explicitly.

## Examples

```bash
# Auto-detect provider from API keys
python vision.py "screenshot.png" "Describe the page layout and any visible UI issues."

# Explicit provider
python vision.py --provider qwen "mockup.png" "List all components, colors, and spacing patterns."

# Custom model
QWEN_MODEL=qvq-max python vision.py --provider qwen "diagram.png" "Explain the architecture."

# GPT-4o for visual regression
python vision.py -p openai "after.png" "Compare with app design spec, flag differences."

# Fully custom provider (self-hosted, third-party proxy, any OpenAI-compatible endpoint)
MYAPI_API_KEY=sk-xxx MYAPI_BASE_URL=https://host/v1 MYAPI_MODEL=my-model \
  python vision.py --provider myapi "ui.png" "Analyze layout issues"
```
