#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THUYRan 原版推理层 skill -> WorkBuddy 适配脚本（个人本机使用）

背景：
  deductive-reasoning / dispute-issue-identification / conflict-resolution
  三个 skill 源自 THUYRan/Legal-Skills-Chinese（CC BY-NC-ND 4.0）。
  本脚本【不包含原版 skill 的任何内容】，只做一件事：
  把原版 SKILL.md frontmatter 里的 description 替换为 WorkBuddy 触发钩子格式，
  使 WorkBuddy 的模型能靠 description 主动识别并调用该 skill（正文一律不动）。

  按 CC BY-NC-ND：个人下载原版、自行修改、本地自用是被允许的，
  本脚本只在你本机修改你下载的原版副本，不产生任何对外分发。

用法：
  python adapt_for_workbuddy.py <skill目录或SKILL.md路径> [更多路径...]
  python adapt_for_workbuddy.py --all <skills根目录>     # 自动处理目录下全部3个推理层skill

效果：
  原文件不改动，每个 skill 生成：
    SKILL.md          -> 已适配（description 改为触发钩子）
    SKILL.md.original -> 原版备份（恢复用：cp SKILL.md.original SKILL.md）
"""

import sys
from pathlib import Path

# stdout 统一 UTF-8，避免 Windows GBK 终端下中文乱码/报错
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# 三个 skill 的 WorkBuddy 触发钩子（本项目的原创描述，替代原版 description）
TRIGGER_DESCRIPTIONS = {
    "dispute-issue-identification": (
        "当用户需要【从案件材料中提取争议焦点】时使用。触发词：争点、争议焦点、焦点、核心争议。\n"
        "输出：争议焦点清单（核心/次级/背景，区分事实争议vs法律争议）。不做：法条检索、三段论推理。"
    ),
    "deductive-reasoning": (
        "当用户需要【把事实和法条组织成三段论推理链】时使用。触发词：推理、三段论、逻辑分析、推导、涵摄。\n"
        "输出：大前提-小前提-结论推理链+有效性验证（指出推理谬误）。不做：法条检索、争点提取。"
    ),
    "conflict-resolution": (
        "当用户需要【裁决法条竞合/规范冲突/证据矛盾】时使用。触发词：竞合、冲突、矛盾、优先适用、排除适用。\n"
        "输出：适用X+排除Y+理由+置信度+类案支撑。不做：法条检索、争点提取。"
    ),
}

TARGET_NAMES = set(TRIGGER_DESCRIPTIONS.keys())


def parse_skill_name(text: str) -> str | None:
    """从 frontmatter 提取 name 字段。"""
    m = __import__("re").search(r"^name:\s*([^\s]+)", text, __import__("re").MULTILINE)
    return m.group(1) if m else None


def split_frontmatter(text: str):
    """
    按行切出 frontmatter。
    返回 (frontmatter行列表, 正文剩余行列表)；frontmatter 缺省返回 (None, lines)。
    """
    lines = text.splitlines()
    if not lines or not lines[0].startswith("---"):
        return None, lines
    end = None
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            end = i
            break
    if end is None:
        return None, lines
    return lines[1:end], lines[end + 1:]


def build_description_block(desc: str) -> list[str]:
    """把多行触发钩子变成 frontmatter 里的 description 块行。"""
    lines = ["description: |"]
    for line in desc.splitlines():
        lines.append("  " + line)
    return lines


def replace_description_in_frontmatter(fm_lines: list[str], new_desc: str) -> list[str]:
    """
    在 frontmatter 行列表里替换 description。
    兼容：
      description: |        (多行块, 后续缩进行)
      description: "..."    (单行双引号)
      description: 单行值
    返回替换后的行列表。
    """
    out = []
    i = 0
    replaced = False
    while i < len(fm_lines):
        line = fm_lines[i]
        stripped = line.lstrip()
        if not replaced and stripped.startswith("description:"):
            # 若下一行是缩进续行(块标量), 一起跳过
            j = i + 1
            while j < len(fm_lines) and fm_lines[j][:1] in (" ", "\t"):
                j += 1
            out.extend(build_description_block(new_desc))
            i = j
            replaced = True
            continue
        out.append(line)
        i += 1
    return out


def adapt_skill(skill_path: Path) -> tuple[str, str]:
    """适配单个 skill，返回 (name, 状态码)。"""
    if skill_path.is_dir():
        skill_path = skill_path / "SKILL.md"
    if not skill_path.is_file():
        return (str(skill_path), "NOT_FOUND")

    raw = skill_path.read_text(encoding="utf-8", errors="replace")
    name = parse_skill_name(raw)
    if name not in TARGET_NAMES:
        return (name or str(skill_path), "NOT_TARGET")

    if "当用户需要【" in raw:
        return (name, "ALREADY")

    fm_lines, body_lines = split_frontmatter(raw)
    if fm_lines is None:
        return (name, "NO_FRONTMATTER")

    new_fm = replace_description_in_frontmatter(fm_lines, TRIGGER_DESCRIPTIONS[name])
    if new_fm == fm_lines:
        return (name, "NO_DESCRIPTION")

    rebuilt = "---\n" + "\n".join(new_fm) + "\n---\n" + "\n".join(body_lines)
    if raw.endswith("\n"):
        rebuilt += "\n"

    backup = skill_path.with_name("SKILL.md.original")
    if not backup.exists():
        backup.write_text(raw, encoding="utf-8")
    skill_path.write_text(rebuilt, encoding="utf-8")
    return (name, "OK")


def main():
    args = sys.argv[1:]
    if not args:
        print("usage: python adapt_for_workbuddy.py <skill-dir|SKILL.md> [...]")
        print("   or: python adapt_for_workbuddy.py --all <skills-root>")
        return 1

    if args[0] == "--all":
        root = Path(args[1])
        targets = []
        for d in sorted(root.iterdir()):
            if d.is_dir() and (d / "SKILL.md").exists():
                targets.append(d)
    else:
        targets = [Path(a) for a in args]

    ok = skip = fail = 0
    for t in targets:
        name, status = adapt_skill(t)
        if status == "OK":
            print(f"[OK]     {name} -> adapted, backup at SKILL.md.original")
            ok += 1
        elif status == "ALREADY":
            print(f"[SKIP]   {name} -> already trigger-hook format, skipped")
            skip += 1
        elif status == "NOT_TARGET":
            print(f"[SKIP]   {name} -> not a reasoning-layer skill, skipped")
            skip += 1
        elif status == "NO_FRONTMATTER":
            print(f"[FAIL]   {name} -> no frontmatter block found")
            fail += 1
        elif status == "NO_DESCRIPTION":
            print(f"[FAIL]   {name} -> description not found in frontmatter")
            fail += 1
        else:
            print(f"[FAIL]   {name} -> file not found")
            fail += 1

    print(f"\nDone: {ok} adapted, {skip} skipped, {fail} failed")
    if ok:
        print("Next: upload the three SKILL.md to WorkBuddy (Skills -> Add -> Upload),")
        print("      and configure orchestration (project Instructions field or")
        print("      .workbuddy/memory/MEMORY.md).")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
