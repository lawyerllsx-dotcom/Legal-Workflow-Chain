# 环境配置 · 02 — 本地 OCR（PP-OCRv6 / PaddleOCR）

> 给 WorkBuddy 的 AI 当引导剧本。目标：装好本地 OCR，处理 PDF/图片里的文字（中文案卷），**不联网、不上传**。
> ⚠️ 这一步较重（装 Python 依赖 + 下载模型约 2.5G），**可选**。不装不影响核心 skill（检索/推理/核查都纯文本可用）。

## 一、OCR 工具脚本

本地 OCR 工具（`ocr.bat` / `ocr_run.py` / `ocr_watch.py` / `ocr_contract.py` / `requirements.txt`）为作者私有，**可向作者索取**。也可以按本文步骤自行搭建 OpenVINO / PaddleOCR 环境。

## 二、安装 Python 环境

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

## 三、OCR 模型与复验机制（V6 + VL）

**两套引擎（内置自动切换，与作者环境一致）**：

| 引擎 | 用途 | 速度 | 说明 |
|------|------|------|------|
| **V6**（默认）| 常规文档 OCR | ~2.8 秒/页 | PP-OCRv6 medium（det / rec / 文本方向）|
| **VL**（复验）| 复杂版式 | ~20 秒/页 | PaddleOCR-VL-1.6，**低产页 / 低置信行自动用 VL 复验**（内置 Auto-fallback 逻辑）|

**模型获取**：
- **V6**：`ocr_contract.py` 里指定 `PP-OCRv6_medium_det/rec`，PaddleOCR **首次运行自动下载**官方模型，无需手动。
- **VL（关键，必须 OpenVINO 版）**：
  - ModelScope 搜 **`zhaohb/PaddleOCR-VL-1.6-ov`**（作者 zhaohb 的 OpenVINO 转换仓库），下载到 `<ocr目录>\PaddleOCR-VL-1.6-ov`
  - 布局模型放 `.cache/modelscope/zhaohb/PaddleOCR-VL-1.5-ov/PP-DoclayoutV3-ov/`
  - 引擎 `github.com/zhaohb/paddleocr_vl_ov`（`requirements.txt` 已引用）
  - ⚠️ **不要下 PyTorch 原版**——脚本引擎只认 OpenVINO（-ov）格式

**验证复验生效**：OCR 一张复杂排版 PDF（有表格/多栏），看输出是否出现 VL 复验提示。

## 四、适配路径（关键）

`ocr.bat` 和 `ocr_run.py` 里写死了原作者的路径，**必须改成你本机的**：

1. 用记事本/VS Code 打开 `ocr.bat`，找到：
   ```
   set PY=D:\ai-models\paddleocr_ov\Scripts\python.exe
   ```
   改成你本机虚拟环境的 python 路径，例如：
   ```
   set PY=C:\ocr-tools\paddleocr_ov\Scripts\python.exe
   ```
2. 同样把脚本里所有 `D:\ai-models` 替换成你的 OCR 目录（搜索替换即可）。

## 五、测试

```
ocr 一个测试.pdf
```

成功 → 同目录生成 `<文件名>.md`（识别文字）。失败 → 按报错排查（多半是路径或模型没放对）。

## 六、和 skill 的配合

装好后，`vision` skill 的使用边界会生效：
- **文字内容**（文档/票据/案卷）→ 走 OCR（本工具）
- **识人识物识场景** → 才用 vision 视觉

> 维护者提醒：OCR 处理的是**本地文件，默认不上传**。涉及把内容发到线上（如云 OCR）的操作，必须先得到你明确同意。
