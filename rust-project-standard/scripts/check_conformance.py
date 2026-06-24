#!/usr/bin/env python3
"""检查一个 Rust workspace 是否符合本规范的关键结构不变量。

用法:
    python check_conformance.py [PROJECT_ROOT]   # 默认当前目录

退出码非 0 表示有违规;适合放进 CI 或 pre-commit。
编译器 + clippy + cargo-deny 那条门(ci.sh)管行为与质量;本脚本管结构。
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

# 厂商 / 重型 SDK 黑名单:domain crate 的依赖里不允许出现(核心抽象零 SDK)
SDK_DENYLIST = frozenset({
    "async-openai", "openai-api-rs", "openai", "anthropic-sdk", "cohere-rust",
    "qdrant-client", "pinecone-sdk", "weaviate-client", "milvus-sdk-rust",
    "aws-sdk-bedrockruntime", "google-generative-ai-rs", "ollama-rs",
    "candle-core", "candle-nn", "tch", "ort", "llm",
})


def _load_toml(path: Path) -> dict | None:
    if not path.is_file():
        return None
    return tomllib.loads(path.read_text(encoding="utf-8"))


def check(root: Path) -> list[str]:
    problems: list[str] = []

    # 1. workspace 根
    ws = _load_toml(root / "Cargo.toml")
    if ws is None:
        problems.append("缺少根 Cargo.toml。")
        return problems
    if "workspace" not in ws:
        problems.append("根 Cargo.toml 不是 workspace(缺 [workspace]);应用多 crate 工作区组织。")

    lints = ws.get("workspace", {}).get("lints", {})
    # 只查工作区根 forbid;确需 unsafe 的 crate 可退出继承、本地降级 deny(见 standard.md §2),不违反本检查。
    if lints.get("rust", {}).get("unsafe_code") != "forbid":
        problems.append("[workspace.lints.rust] 未设 unsafe_code = \"forbid\"。")
    if not lints.get("clippy"):
        problems.append("[workspace.lints.clippy] 未配置严格 lint(门禁 -D warnings 依赖它)。")

    # 2. 工具链/闸/门禁文件
    for f, why in [
        ("rust-toolchain.toml", "钉死工具链版本"),
        ("deny.toml", "cargo-deny:license/安全/依赖闸"),
        ("ci.sh", "唯一零警告门"),
        ("CLAUDE.md", "根级路由表"),
    ]:
        if not (root / f).is_file():
            problems.append(f"缺少 {f}({why})。")

    # 3. domain crate 零 SDK 依赖
    domain_toml = _load_toml(root / "crates" / "domain" / "Cargo.toml")
    if domain_toml is None:
        problems.append("缺少 crates/domain/Cargo.toml(领域抽象 crate)。")
    else:
        deps = set(domain_toml.get("dependencies", {}).keys())
        leaked = deps & SDK_DENYLIST
        if leaked:
            problems.append(
                f"crates/domain 依赖了厂商 SDK {sorted(leaked)}:"
                "domain 必须零 SDK,provider 实现放 adapters。"
            )

    # 4. 每个 crate 都有 CLAUDE.md
    crates_dir = root / "crates"
    crate_dirs = []
    if crates_dir.is_dir():
        crate_dirs += [d for d in crates_dir.iterdir() if d.is_dir() and (d / "Cargo.toml").is_file()]
    app_dir = root / "app"
    if (app_dir / "Cargo.toml").is_file():
        crate_dirs.append(app_dir)
    for d in crate_dirs:
        if not (d / "CLAUDE.md").is_file():
            problems.append(f"{d.relative_to(root)} 缺少 CLAUDE.md(每个 crate 需就近契约)。")

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
