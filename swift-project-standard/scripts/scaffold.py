#!/usr/bin/env python3
"""按 swift-project-standard 生成一个新 SwiftPM(target-per-domain)项目骨架。

用法:
    python scaffold.py <package_name> [--target DIR] [--domains A B C] [--app]

例:
    python scaffold.py MyRagApp --target ~/code --domains Retrieval Generation Agents

整树镜像 assets/templates/(把 `__PACKAGE__` 换成包名),并为每个领域创建一个 target
骨架(`Sources/<Domain>/<Domain>.swift` + `Sources/<Domain>/CLAUDE.md`)。

SPM 没有 Cargo 的 `members=["crates/*"]` glob —— 每个 target 必须在 Package.swift
显式列出。因此本脚本向模板的三处哨兵注入领域 target:
  - `/* __DOMAIN_PRODUCT_TARGETS__ */`  → AppCore product 的 targets 列表
  - `/* __DOMAIN_APP_DEPS__ */`         → App target 的 dependencies 列表
  - `// __DOMAIN_TARGETS_START__` / `// __DOMAIN_TARGETS_END__` → targets 数组里的 `.target(...)` 块

领域名直接作为 **target 名 + 目录名 + 类型名**,因此必须是合法的 Swift 模块标识符
(字母或下划线开头,其后字母/数字/下划线)。文档示例用首字母大写的 `Retrieval Generation`;
脚本原样使用你传入的名字,不做大小写转换。

之后:cd 进项目 → `./ci.sh`(完整零警告门)。
"""
from __future__ import annotations

import argparse
import stat
import subprocess
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
PLACEHOLDER = "__PACKAGE__"

# Package.swift 里的哨兵标记(必须与模板严格一致)。
SENTINEL_PRODUCT_TARGETS = "/* __DOMAIN_PRODUCT_TARGETS__ */"
SENTINEL_APP_DEPS = "/* __DOMAIN_APP_DEPS__ */"
SENTINEL_TARGETS_START = "// __DOMAIN_TARGETS_START__"
SENTINEL_TARGETS_END = "// __DOMAIN_TARGETS_END__"

_SWIFT_KEYWORDS = frozenset({
    "associatedtype", "class", "deinit", "enum", "extension", "func", "import",
    "init", "inout", "internal", "let", "operator", "private", "protocol",
    "public", "static", "struct", "subscript", "typealias", "var", "where",
})


def _valid_identifier(name: str) -> bool:
    """合法 Swift 标识符:字母/下划线开头,其余字母/数字/下划线,且非关键字。"""
    if not name:
        return False
    if not (name[0].isalpha() or name[0] == "_"):
        return False
    if not all(c.isalnum() or c == "_" for c in name):
        return False
    return name not in _SWIFT_KEYWORDS


def _domain_source(name: str) -> str:
    return f"""// {name}:领域逻辑。只经 `Domain` 的 ports 调外部依赖,绝不依赖 `Adapters` 或厂商 SDK。
//
// 注入 `any LLM` / `any Embedder`(Domain ports),用 newtype/强类型表达不变量,
// 不静默失败(`throws` 向上传播)。详见 swift-protocols / swift-concurrency。

import Domain
import Kernel

/// {name} 领域逻辑入口。
///
/// 依赖方向:`{name}` → `Domain` + `Kernel`。**绝不**依赖 `Adapters` 或具体 SDK ——
/// 外部依赖只经构造注入的 Domain port 使用,这样换实现/换模型不需要改本 target。
public struct {name}: Sendable {{
    public init() {{}}
}}
"""


def _domain_claude_md(name: str) -> str:
    return f"""# target: {name} — 契约

职责:领域逻辑 —— {name}。用 `Domain` 的 ports + 自己的 models/逻辑。
- 依赖注入 Domain port(如 `any LLM` / `any Embedder`),**绝不**依赖 `Adapters` 或具体 SDK。
- 用 newtype/强类型表达不变量;非法状态尽量不可表示(parse, don't validate)。
- 不静默失败:错误用 `throws` 向上传播(provider 失败归一到 `ProviderError`)。
- 结构尽量深:子能力拆子文件/子类型,命名即定位。
- 上游:`Domain` + `Kernel`;下游:`App`(或 Xcode app 壳)注入并调用。
"""


def _target_block(name: str) -> str:
    """单个领域 target 的 `.target(...)` 声明(4 空格缩进,与模板对齐)。"""
    return (
        f'        .target(\n'
        f'            name: "{name}",\n'
        f'            dependencies: ["Domain", "Kernel"],\n'
        f'            exclude: ["CLAUDE.md"],\n'
        f'            swiftSettings: [.swiftLanguageMode(.v6)]\n'
        f'        ),\n'
    )


def _inject_domains(manifest: str, domains: list[str]) -> str:
    """把领域 target 注入 Package.swift 的三处哨兵。"""
    for sentinel in (SENTINEL_PRODUCT_TARGETS, SENTINEL_APP_DEPS):
        if sentinel not in manifest:
            raise SystemExit(f"Package.swift 模板缺少哨兵 {sentinel!r},无法注入领域。")
    if SENTINEL_TARGETS_START not in manifest or SENTINEL_TARGETS_END not in manifest:
        raise SystemExit("Package.swift 模板缺少 START/END 哨兵,无法注入领域 target。")

    if not domains:
        # 无领域:去掉两个内联哨兵注释(避免留下无意义的 /* ... */),START/END 留空。
        manifest = manifest.replace(f' {SENTINEL_PRODUCT_TARGETS}', "")
        manifest = manifest.replace(f' {SENTINEL_APP_DEPS}', "")
        return manifest

    # 1. product targets 与 app deps:把内联哨兵替换为 `, "A", "B"`。
    name_list = ", ".join(f'"{d}"' for d in domains)
    manifest = manifest.replace(SENTINEL_PRODUCT_TARGETS, f", {name_list}")
    manifest = manifest.replace(SENTINEL_APP_DEPS, f", {name_list}")

    # 2. targets 数组:在 START/END 之间插入 `.target(...)` 块。
    blocks = "".join(_target_block(d) for d in domains)
    start = manifest.index(SENTINEL_TARGETS_START)
    end = manifest.index(SENTINEL_TARGETS_END) + len(SENTINEL_TARGETS_END)
    # 保留 START 行本身,在其后插入领域块,再接 END 行。
    head = manifest[: start + len(SENTINEL_TARGETS_START)]
    tail = manifest[manifest.index(SENTINEL_TARGETS_END):]
    manifest = f"{head}\n{blocks}        {tail}"
    return manifest


def _make_app_shell(target: Path, package: str) -> None:
    """为 `--app` 创建一个最小 SwiftUI app 壳(project.yml 的 sources 指向 AppShell/)。"""
    shell = target / "AppShell"
    shell.mkdir(parents=True, exist_ok=True)
    (shell / "App.swift").write_text(
        f"""// 瘦 app 壳:只做 UI 与组装,领域逻辑全在 SwiftPM package(import AppCore)。
import AppCore
import SwiftUI

@main
struct {package}App: App {{
    var body: some Scene {{
        WindowGroup {{
            ContentView()
        }}
    }}
}}

struct ContentView: View {{
    var body: some View {{
        Text("{package}")
            .padding()
    }}
}}
""",
        encoding="utf-8",
    )


def scaffold(package: str, target: Path, domains: list[str], app: bool) -> None:
    if not _valid_identifier(package):
        raise SystemExit(
            f"包名非法(需合法 Swift 标识符:字母/下划线开头,其后字母/数字/下划线):{package!r}"
        )
    seen: set[str] = set()
    for dom in domains:
        if not _valid_identifier(dom):
            raise SystemExit(
                f"领域名非法(需合法 Swift 模块标识符):{dom!r}。示例:Retrieval Generation"
            )
        if dom in {"Kernel", "Domain", "Adapters", "App", "SmokeTests", "ConformanceTests", "AppCore"}:
            raise SystemExit(f"领域名与内置 target 冲突:{dom!r}。请换名。")
        if dom in seen:
            raise SystemExit(f"领域名重复:{dom!r}。")
        seen.add(dom)

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"目标目录非空:{target}。请换一个空目录或不存在的路径。")

    # 1. 整树镜像 + 占位替换。Package.swift 单独处理(要注入领域)。
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = src.relative_to(TEMPLATES)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(PLACEHOLDER, package)
        if rel.name == "Package.swift":
            text = _inject_domains(text, domains)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. 领域 target 骨架(Sources/<Domain>/<Domain>.swift + CLAUDE.md)。
    for dom in domains:
        d = target / "Sources" / dom
        d.mkdir(parents=True, exist_ok=True)
        (d / f"{dom}.swift").write_text(_domain_source(dom), encoding="utf-8")
        (d / "CLAUDE.md").write_text(_domain_claude_md(dom), encoding="utf-8")

    # 3.(可选)生成 Xcode app 壳。
    if app:
        _make_app_shell(target, package)
        try:
            subprocess.run(
                ["xcodegen", "generate"],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"✓ 已用 xcodegen 生成 {package}App.xcodeproj")
        except FileNotFoundError:
            print("⚠ 未找到 xcodegen(brew install xcodegen);已留下 project.yml + AppShell/,")
            print("  装好后在项目根跑 `xcodegen generate` 即可生成 .xcodeproj。")
        except subprocess.CalledProcessError as exc:
            print("⚠ xcodegen generate 失败(已留下 project.yml + AppShell/):")
            print((exc.stderr or exc.stdout or "").strip())

    print(f"✓ 已生成 SwiftPM 包:{target}")
    print(f"  领域 target:{', '.join(domains) if domains else '(无)'}")
    print("  下一步:")
    print(f"    cd {target}")
    print("    swift build            # 首次编译(默认离线、零 SDK)")
    print("    ./ci.sh                # 完整零警告门(swift-format + swiftlint + build + test)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="按 swift-project-standard 生成 SwiftPM(target-per-domain)骨架。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "领域名直接用作 target 名 / 目录名 / 类型名,须是合法 Swift 模块标识符。\n"
            "约定首字母大写,如:--domains Retrieval Generation Agents"
        ),
    )
    ap.add_argument("package", help="包名 / 可执行名(合法 Swift 标识符,字母或下划线开头)")
    ap.add_argument("--target", default=".", help="目标目录(默认:当前目录下 <package>/)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["Retrieval", "Generation"],
        metavar="DOMAIN",
        help="领域 target 名(默认:Retrieval Generation)。传 `--domains` 不带值则不生成领域。",
    )
    ap.add_argument(
        "--app",
        action="store_true",
        help="额外生成 Xcode app 壳(写 AppShell/ 并调用 xcodegen generate;未装 xcodegen 时优雅跳过)。",
    )
    args = ap.parse_args()

    base = Path(args.target).resolve()
    target = base / args.package if args.target == "." else base
    scaffold(args.package, target, list(args.domains), args.app)


if __name__ == "__main__":
    main()
