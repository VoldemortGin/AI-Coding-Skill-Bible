#!/usr/bin/env python3
"""按本规范生成一个新 Python 项目骨架。

用法:
    python scaffold.py <package_name> [--target DIR] [--domains a b c]

例:
    python scaffold.py myrag --target ~/code/myrag --domains ingestion retrieval generation agents

整树镜像 assets/templates/(src_pkg → src/<package>),替换 __PACKAGE_NAME__,
并创建可导航的领域骨架。之后:cd 进项目 → `uv sync` → `./ci.sh`。
"""
from __future__ import annotations  # 此脚本独立运行,不属于受检包

import argparse
import stat
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PLACEHOLDER = "__PACKAGE_NAME__"


def _target_rel(rel: Path, package: str) -> Path:
    """把模板内相对路径映射到项目内路径(src_pkg → src/<package>)。"""
    parts = list(rel.parts)
    if parts and parts[0] == "src_pkg":
        parts = ["src", package, *parts[1:]]
    return Path(*parts)


def scaffold(package: str, target: Path, domains: list[str]) -> None:
    if not package.isidentifier():
        raise SystemExit(f"包名非法(必须是合法 Python 标识符):{package!r}")
    for d in domains:
        if not d.isidentifier():
            raise SystemExit(f"领域名非法:{d!r}")

    # 1. 整树镜像 + 占位替换
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = target / _target_rel(rel, package)
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(PLACEHOLDER, package)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):  # ci.sh 可执行
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. 可导航的领域骨架(domain-first,见规范 §7.9)
    pkg_dir = target / "src" / package
    for d in domains:
        (pkg_dir / d).mkdir(parents=True, exist_ok=True)
        (pkg_dir / d / "__init__.py").write_text(
            f"# 领域:{d}。可 re-export 公共 API(此包在 beartype hook 之后导入,被检查)。\n",
            encoding="utf-8",
        )

    # 3. 运行期可写目录占位
    for d in ("data", "logs"):
        keep = target / d / ".gitkeep"
        keep.parent.mkdir(parents=True, exist_ok=True)
        keep.touch()

    print(f"✓ 已生成项目:{target}")
    print("  下一步:")
    print(f"    cd {target}")
    print("    uv sync            # 一次性 editable 安装,之后改 src/ 即时生效")
    print("    uv run pytest      # beartype O1")
    print("    ./ci.sh            # 完整零警告门(也可 make check)")


def main() -> None:
    ap = argparse.ArgumentParser(description="按 python-project-standard 生成项目骨架。")
    ap.add_argument("package", help="包名(合法 Python 标识符,如 myrag)")
    ap.add_argument("--target", default=".", help="目标目录(默认当前)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["ingestion", "retrieval", "generation", "agents", "pipelines"],
        help="按 domain-first 创建的领域包(见 §7.9)",
    )
    args = ap.parse_args()
    base = Path(args.target).resolve()
    target = base / args.package if args.target == "." else base
    scaffold(args.package, target, list(args.domains))


if __name__ == "__main__":
    main()
