#!/usr/bin/env python3
"""检查一个 Python 项目是否符合本规范的关键结构不变量。

用法:
    python check_conformance.py [PROJECT_ROOT]   # 默认当前目录

退出码非 0 表示有违规;适合放进 CI 或 pre-commit。
这是规范里少数可"硬强制"的部分——其余靠 ci.sh 那条门 + skill 让 AI 默认遵循。
"""
from __future__ import annotations  # 此脚本独立运行,不属于受检包

import ast
import sys
import tomllib
from pathlib import Path

# 厂商 / 重型 SDK 黑名单:这些只允许出现在 adapters/ 下(核心与领域代码零 SDK import)
SDK_DENYLIST = frozenset({
    "openai", "anthropic", "cohere", "voyageai", "mistralai", "google",
    "qdrant_client", "pinecone", "weaviate", "chromadb", "pymilvus", "lancedb",
    "transformers", "sentence_transformers", "torch", "vllm",
    "langchain", "llama_index", "boto3",
})


def _find_package(root: Path) -> tuple[Path | None, list[str]]:
    problems: list[str] = []
    src = root / "src"
    if not src.is_dir():
        problems.append("缺少 src/ 目录:必须用 src 布局(src/<pkg>/)。")
        return None, problems
    pkgs = [d for d in src.iterdir() if d.is_dir() and (d / "__init__.py").is_file()]
    if not pkgs:
        problems.append("src/ 下没有含 __init__.py 的包目录。")
        return None, problems
    if len(pkgs) > 1:
        problems.append(f"src/ 下有多个包目录({', '.join(p.name for p in pkgs)});应只有一个。")
    pkg = pkgs[0]
    if pkg.name == "src":
        problems.append("包名是 'src':请用真实包名(自用也别 import src)。")
    return pkg, problems


def _module_has_code(path: Path) -> bool:
    body = ast.parse(path.read_text(encoding="utf-8")).body
    if not body:
        return False
    if len(body) == 1 and isinstance(body[0], ast.Expr) and isinstance(
        getattr(body[0], "value", None), ast.Constant
    ):
        return False  # 仅 docstring
    return True


def _has_relative_import(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return any(
        isinstance(n, ast.ImportFrom) and n.level and n.level > 0 for n in ast.walk(tree)
    )


def _imported_top_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    mods: set[str] = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                mods.add(a.name.split(".")[0])
        elif isinstance(n, ast.ImportFrom) and not n.level and n.module:
            mods.add(n.module.split(".")[0])
    return mods


def check(root: Path) -> list[str]:
    problems: list[str] = []
    pkg, pkg_problems = _find_package(root)
    problems.extend(pkg_problems)

    if pkg is not None:
        init = pkg / "__init__.py"
        text = init.read_text(encoding="utf-8")
        if "beartype_this_package" not in text and "beartype.claw" not in text:
            problems.append(f"{init.relative_to(root)} 未安装 beartype claw hook。")

        core = pkg / "core"
        if not core.is_dir():
            problems.append("缺少 core/:settings/logging/paths/prompts 的统一来源。")
        else:
            core_init = core / "__init__.py"
            if not core_init.is_file():
                problems.append("缺少 core/__init__.py。")
            elif _module_has_code(core_init):
                problems.append("core/__init__.py 含代码:必须保持空(否则 paths/logging 等会在 hook 前被导入而漏检)。")
            settings = core / "settings.py"
            if not settings.is_file():
                problems.append("缺少 core/settings.py。")
            elif _has_relative_import(settings):
                problems.append("core/settings.py 有相对导入:它必须是 beartype 叶子,不能 import 一方模块。")

        # 模型无关:厂商 SDK 只允许在 adapters/ 下出现
        adapters = pkg / "adapters"
        for py in pkg.rglob("*.py"):
            try:
                rel_to_adapters = py.relative_to(adapters)  # noqa: F841
                continue  # 在 adapters/ 下,允许 import SDK
            except ValueError:
                pass
            leaked = _imported_top_modules(py) & SDK_DENYLIST
            if leaked:
                problems.append(
                    f"{py.relative_to(root)} import 了厂商 SDK {sorted(leaked)}:"
                    "SDK 只允许在 adapters/ 下(核心/领域代码零 SDK,经 ports/ 的 Protocol 调用)。"
                )

    pyproject = root / "pyproject.toml"
    if not pyproject.is_file():
        problems.append("缺少 pyproject.toml。")
    else:
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        if data.get("tool", {}).get("mypy", {}).get("strict") is not True:
            problems.append("pyproject [tool.mypy] 未设 strict = true。")

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    problems = check(root)
    if problems:
        print(f"✗ 不符合规范({len(problems)} 项):\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("✓ 通过关键结构检查。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
