# -*- coding: utf-8 -*-
r"""
ocr_run.py — 中文路径 OCR 辅助脚本
====================================
解决 Git Bash harness 下中文路径 argv 乱码问题（Git Bash → Windows Python 传参用 ANSI 码页，
中文必乱）。方案：路径写进 UTF-8 文件，脚本读取后复制为 ASCII 临时名再跑 OCR，跑完清理。

用法：
  1. 用 Write 工具把目标写入 targets.txt（UTF-8，每行一条，格式：源路径|输出目录|选项）
     例：
       D:\案件\xxx\裁定书.pdf|D:\ai-models\output|-q --verify --extract --summary
     输出目录可省略（默认 D:\ai-models\output），选项可省略（默认 -q --verify --extract --summary）
  2. 运行：python D:/ai-models/ocr_run.py

注意：本脚本仅处理 argv 编码问题，不修改任何源文件（只复制到临时目录，跑完删除临时副本）。
"""
import os, sys, shutil, subprocess

TMP_DIR    = r"D:\ai-models\tmp_ocr"
TARGETS    = os.path.join(TMP_DIR, "targets.txt")
PY         = r"D:\ai-models\paddleocr_ov\Scripts\python.exe"
CONTRACT   = r"D:\ai-models\ocr_contract.py"
DEFAULT_OUT = r"D:\ai-models\output"
DEFAULT_OPT = "-q --verify --extract --summary"

os.makedirs(TMP_DIR, exist_ok=True)

if not os.path.exists(TARGETS):
    print(f"[ERROR] 未找到 targets.txt：{TARGETS}")
    print("先用 Write 工具写入目标（UTF-8，每行：源路径|输出目录|选项）")
    sys.exit(1)

with open(TARGETS, encoding="utf-8") as f:
    lines = [l.strip() for l in f if l.strip() and not l.startswith("#")]

if not lines:
    print("[ERROR] targets.txt 为空")
    sys.exit(1)

for i, line in enumerate(lines, 1):
    parts = [p.strip() for p in line.split("|")]
    src, out_dir, opts = parts[0], (parts[1] if len(parts) > 1 else DEFAULT_OUT), (parts[2] if len(parts) > 2 else DEFAULT_OPT)

    if not os.path.exists(src):
        print(f"[{i}/{len(lines)}] [SKIP] 文件不存在：{src}")
        continue

    work = os.path.join(TMP_DIR, f"work_{i}.pdf")
    shutil.copy2(src, work)
    print(f"[{i}/{len(lines)}] {os.path.basename(src)}  ->  {work}")

    cmd = [PY, CONTRACT, work, out_dir] + opts.split()
    rc = subprocess.run(cmd).returncode

    # 输出文件以 work_N 命名，改回原文件名（{原stem}.md/_facts/_quality/.entities.json）
    orig_stem = os.path.splitext(os.path.basename(src))[0]
    work_stem = os.path.splitext(os.path.basename(work))[0]
    for suffix in ["", "_facts", "_quality"]:
        src_f = os.path.join(out_dir, f"{work_stem}{suffix}.md")
        dst_f = os.path.join(out_dir, f"{orig_stem}{suffix}.md")
        if os.path.exists(src_f):
            if os.path.exists(dst_f):
                os.remove(dst_f)  # 同名旧输出（重跑）直接覆盖
            os.rename(src_f, dst_f)
    ent_src = os.path.join(out_dir, f"{work_stem}.entities.json")
    ent_dst = os.path.join(out_dir, f"{orig_stem}.entities.json")
    if os.path.exists(ent_src):
        if os.path.exists(ent_dst):
            os.remove(ent_dst)
        os.rename(ent_src, ent_dst)

    if os.path.exists(work):
        os.remove(work)
    if rc != 0:
        print(f"[{i}/{len(lines)}] [FAIL] rc={rc}")
    else:
        print(f"[{i}/{len(lines)}] [OK] 输出：{os.path.join(out_dir, orig_stem)}*.md")

print("全部完成。清理 targets.txt？可手动删除：", TARGETS)