# 环境配置 · 02 — 本地 OCR（两档：通用 V6 / 完整 V6+VL）

> 给 WorkBuddy 的 AI 当引导剧本。目标：装好本地 OCR，处理 PDF/图片里的文字（中文案卷），**不联网、不上传**。
> 工具脚本（`ocr.bat` / `ocr_run.py` / `ocr_watch.py` / `ocr_contract.py` / `requirements.txt`）随本包提供于 `tools/ocr/`，按本文适配本机路径即可。

## 一、先选档（关键）

| 档 | 内容 | 模型 | 依赖 | 速度 | 适合 |
|----|------|------|------|------|------|
| **通用档**（✅ 推荐默认）| V6 常规识别 | ~232M（PaddleOCR 自动下载）| 轻 | ~2.8 秒/页 | 绝大多数案卷/合同/票据（白底印刷体）|
| **完整档**（可选增强）| V6 + VL 复验 | +约 2.5G | 重 | 复验时 +~20 秒/页 | 复杂版式：表格/多栏/手写/低质量扫描件 |

**默认推荐通用档**——门槛低、日常够用。**完整档是增强**，遇到复杂版式再装。
选完整档的，装完基础后看 [06-VL完整档适配指南](06-VL完整档适配指南.md) 引导测试与调整。

> 不装 VL 完全没问题：`ocr_contract.py` 内置降级——VL 模型/依赖缺失时自动跳过复验，只用 V6 结果，不报错中断。

## 二、OCR 工具脚本

OCR 工具脚本（`ocr.bat` / `ocr_run.py` / `ocr_watch.py` / `ocr_contract.py` / `requirements.txt`）在 `tools/ocr/`，直接用即可；也可按本文自行搭建 OpenVINO / PaddleOCR 环境。

## 三、通用档：装 Python 环境

1. 装 **Python 3.11+**（[python.org](https://www.python.org/downloads/)，勾选 "Add to PATH"）
2. 建虚拟环境：
   ```
   cd <你的 OCR 工具目录>
   python -m venv paddleocr_ov
   ```
3. 激活并装依赖（约 5-10 分钟）：
   ```
   paddleocr_ov\Scripts\activate
   pip install -r requirements.txt
   ```

## 四、通用档：适配路径（关键）

`ocr.bat` / `ocr_run.py` / `ocr_contract.py` 里写死了作者的路径，**必须改成你本机的**：

1. 打开 `ocr_contract.py`，找到并改这几处（搜索替换）：
   - `MODEL_DIR = Path(r'D:\ai-models')` → 你的 OCR 目录（如 `C:\ocr-tools`）
   - `PADDLEX_HOME` / `MODELSCOPE_CACHE` 两个环境变量 → 同步改成你的目录
2. 打开 `ocr.bat`，改 `set PY=D:\ai-models\...` → 你虚拟环境的 python 路径
3. 把脚本里所有 `D:\ai-models` 替换成你的 OCR 目录

> 通用档**不需要**配 VL 模型路径；脚本在 VL 缺失时自动跳过复验。

## 五、通用档：测试

```
ocr 一个测试.pdf
```

成功 → 同目录生成 `<文件名>.md`。失败 → 按报错排查（多半是路径或依赖）。

## 六、完整档（+VL）：按 06 适配指南

需要表格/多栏/低质量扫描件的高质量识别，或想验证 VL 效果时：
- 按 [06-VL完整档适配指南](06-VL完整档适配指南.md) 确认依赖 + 改路径（**VL 模型引擎首次自动下载**，无需手动）+ 验证测试 + 调整

## 七、和 skill 的配合 + 安全

- 装好后，`vision` skill 的使用边界生效：**文字内容走 OCR，识人识物识场景才用 vision**
- 铁律：OCR 处理**本地文件，默认不上传**；涉及把内容发到线上（云 OCR）必须先经你明确同意
