#!/usr/bin/env python3
"""按本规范生成一个新 Rust(Cargo workspace)项目骨架。

用法:
    python scaffold.py <project_name> [--target DIR] [--domains a b c]

例:
    python scaffold.py myrag --target ~/code/myrag --domains ingestion retrieval generation agents

整树镜像 assets/templates/(替换 __PROJECT__),并为每个领域创建一个 crate 骨架
(workspace members = ["crates/*", "app"],glob 自动纳入)。之后:cd 进项目 → `./ci.sh`。
"""
from __future__ import annotations

import argparse
import stat
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PLACEHOLDER = "__PROJECT__"


def _valid_crate_name(name: str) -> bool:
    return name.replace("_", "a").replace("-", "a").isalnum() and name[0].isalpha()


def _domain_crate(crates_dir: Path, name: str) -> None:
    d = crates_dir / name
    (d / "src").mkdir(parents=True, exist_ok=True)
    (d / "Cargo.toml").write_text(
        f"""[package]
name = "{name}"
version = "0.1.0"
edition.workspace = true
rust-version.workspace = true

[lints]
workspace = true

[dependencies]
domain = {{ path = "../domain" }}
kernel = {{ path = "../kernel" }}
# 领域逻辑 crate:依赖 domain(ports/models)+ kernel,**不**依赖 adapters 或厂商 SDK。
""",
        encoding="utf-8",
    )
    (d / "src" / "lib.rs").write_text(
        f"//! {name}:领域逻辑。只经 `domain` 的 trait 调外部依赖,不碰具体 SDK。\n",
        encoding="utf-8",
    )
    (d / "CLAUDE.md").write_text(
        f"""# crate: {name} — 契约

职责:{name} 领域逻辑。
- 只经 `domain::ports` 的 trait 使用外部 AI 依赖,**不**依赖 adapters/厂商 SDK。
- 用 newtype/强类型表达不变量;不静默失败(`Result`/`?`)。
- 结构尽量深:子模块按子能力拆,命名即定位。
""",
        encoding="utf-8",
    )


def scaffold(project: str, target: Path, domains: list[str]) -> None:
    if not _valid_crate_name(project):
        raise SystemExit(f"项目名非法(字母开头、字母数字/_/-):{project!r}")
    for dom in domains:
        if not _valid_crate_name(dom):
            raise SystemExit(f"领域名非法:{dom!r}")

    # 1. 整树镜像 + 占位替换
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(PLACEHOLDER, project)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. 领域 crate 骨架(domain-first;workspace glob 自动纳入)
    for dom in domains:
        _domain_crate(target / "crates", dom)

    print(f"✓ 已生成 workspace:{target}")
    print("  下一步:")
    print(f"    cd {target}")
    print("    cargo check                # 首次拉依赖并编译")
    print("    ./ci.sh                    # 完整零警告门(需 cargo install cargo-deny;也可 just check)")


def main() -> None:
    ap = argparse.ArgumentParser(description="按 rust-project-standard 生成 Cargo workspace 骨架。")
    ap.add_argument("project", help="项目/二进制名(字母开头)")
    ap.add_argument("--target", default=".", help="目标目录(默认当前)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["ingestion", "retrieval", "generation", "agents", "pipelines"],
        help="按 domain-first 创建的领域 crate",
    )
    args = ap.parse_args()
    base = Path(args.target).resolve()
    target = base / args.project if args.target == "." else base
    scaffold(args.project, target, list(args.domains))


if __name__ == "__main__":
    main()
