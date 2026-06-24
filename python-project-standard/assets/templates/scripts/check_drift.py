#!/usr/bin/env python3
"""文档/工件漂移守卫:扫描带 `covers:` 元数据的文档,确认其引用的代码路径仍存在。

引用失效即 CI 红——把"文档骗了 AI"这个最大隐性成本装上真实性保险丝。
最小实现做路径存在性;可扩展到符号级反射解析(改名/删除即红)。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
COVERS = re.compile(r"^\s*covers:\s*(.+)$", re.MULTILINE)


def main() -> int:
    problems: list[str] = []
    for md in ROOT.rglob("*.md"):
        if any(part in {".git", "node_modules"} for part in md.parts):
            continue
        for m in COVERS.finditer(md.read_text(encoding="utf-8")):
            for raw in m.group(1).split(","):
                p = raw.strip().strip("[]\"' ")
                if p and not (ROOT / p).exists():
                    problems.append(f"{md.relative_to(ROOT)} -> covers 失效路径: {p}")
    if problems:
        print("✗ 文档漂移:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ 无文档漂移。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
