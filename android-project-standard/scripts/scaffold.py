#!/usr/bin/env python3
"""按 android-project-standard 生成一个新的 Gradle multi-module(module-per-domain)骨架。

用法:
    python scaffold.py <app_id> [--target DIR] [--domains a b c]

例:
    python scaffold.py com.example.notes --target ~/code/notes --domains retrieval generation

整树镜像 assets/templates/,做两类替换:
  - **文件内容**里的 `__APP_ID__` → app id(dotted,如 `com.example.notes`)。
  - **目录路径**里的 `__PKG_PATH__` → app id 的 `/` 形式(如 `com/example/notes`),即 Kotlin 源码
    的包目录。这两者耦合(PKG_PATH = APP_ID 把 `.` 换成 `/`),用户只需给一个 app id。

Gradle 没有 Cargo 的 `members=["*"]` glob —— 每个 module 必须在 settings.gradle.kts 显式 `include`。
因此本脚本向两处哨兵注入领域 feature module:
  - settings.gradle.kts 的 `// __DOMAIN_MODULES__`  → `include(":<name>")` 行
  - app/build.gradle.kts 的 `// __DOMAIN_APP_DEPS__` → `implementation(project(":<name>"))` 行
并为每个领域生成一个 `kotlin("jvm")` feature module(只依赖 :domain + :kernel)。

之后:cd 进项目 → `gradle wrapper --gradle-version 8.11.1`(首次)→ `./ci.sh`(完整零警告门)。
"""
from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
from pathlib import Path

TEMPLATES = Path(__file__).resolve().parent.parent / "assets" / "templates"
APP_ID_PLACEHOLDER = "__APP_ID__"
PKG_PATH_PLACEHOLDER = "__PKG_PATH__"

SENTINEL_SETTINGS = "// __DOMAIN_MODULES__"
SENTINEL_APP_DEPS = "// __DOMAIN_APP_DEPS__"

GRADLE_VERSION = "8.11.1"

# Kotlin/Java 硬关键字(不可作 package 段或 module 名,否则需反引号)。
_KEYWORDS = frozenset({
    "package", "import", "class", "interface", "object", "fun", "val", "var",
    "is", "in", "as", "if", "else", "when", "for", "while", "do", "return",
    "true", "false", "null", "this", "super", "typealias", "typeof", "try",
    "catch", "finally", "throw", "break", "continue", "internal", "private",
    "public", "protected", "open", "abstract", "final", "const", "by",
    "int", "long", "short", "byte", "char", "boolean", "float", "double",
    "new", "void", "static", "default", "enum", "extends", "implements",
})

# 内置固定 module —— 领域名不可与之冲突。
_RESERVED_MODULES = frozenset({"app", "kernel", "domain", "adapters"})

_SEGMENT_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_DOMAIN_RE = re.compile(r"^[a-z][a-z0-9]*$")


def _valid_app_id(app_id: str) -> bool:
    """合法 Android applicationId:≥2 段,每段小写字母开头、其后小写字母/数字/下划线,非关键字。"""
    segments = app_id.split(".")
    if len(segments) < 2:
        return False
    return all(_SEGMENT_RE.match(s) and s not in _KEYWORDS for s in segments)


def _valid_domain(name: str) -> bool:
    """合法领域名:同时是合法 Gradle module 名 + Kotlin 包段(小写字母开头,其后小写字母/数字)。"""
    return bool(_DOMAIN_RE.match(name)) and name not in _KEYWORDS


def _pascal(name: str) -> str:
    return name[:1].upper() + name[1:]


def _domain_build_gradle() -> str:
    return """// :__DOMAIN__ —— 领域逻辑。依赖 :domain + :kernel,绝不依赖 :adapters / SDK。

plugins {
    alias(libs.plugins.kotlin.jvm)
    alias(libs.plugins.detekt)
    alias(libs.plugins.ktlint)
}

kotlin {
    explicitApi()
    jvmToolchain(17)
    compilerOptions {
        allWarningsAsErrors.set(true)
    }
}

detekt {
    buildUponDefaultConfig = true
    config.setFrom(rootProject.files("config/detekt/detekt.yml"))
}

dependencies {
    implementation(project(":domain"))
    implementation(project(":kernel"))

    testImplementation(libs.kotlin.test)
}
"""


def _domain_claude_md(name: str) -> str:
    return f"""# module: :{name} — 契约

职责:领域逻辑 —— {name}。用 `:domain` 的 ports + 自己的 model / 逻辑。
- 外部依赖只经构造注入的 `:domain` port(`Llm` / `Embedder`)使用,**绝不**依赖 `:adapters` 或厂商 SDK —— 换实现 / 换模型不必改本 module。
- 用 `@JvmInline value class` newtype 让非法状态不可表示(parse, don't validate)。
- 不静默失败:错误向上抛(provider 边界失败由 adapter 归一到 `ProviderError`)。
- 结构尽量深:子能力拆子文件 / 子类型,命名即定位。
- 依赖方向:上游 `:domain` + `:kernel`;下游 `:app`(组合根)注入实现并调用。
"""


def _domain_source(app_id: str, name: str) -> str:
    pascal = _pascal(name)
    return f"""// {name}:领域逻辑。只经 `:domain` 的 ports 调外部依赖,绝不依赖 `:adapters` 或厂商 SDK。
//
// 注入 `Llm` / `Embedder`(Domain port),用 newtype/强类型表达不变量,不静默失败(向上抛)。

package {app_id}.{name}

import {app_id}.domain.Llm

/**
 * {pascal} 领域逻辑入口。注入 [Llm](Domain port),不碰具体实现。
 *
 * 依赖方向:`:{name}` → `:domain` + `:kernel`。**绝不**依赖 `:adapters` 或具体 SDK ——
 * 外部依赖只经构造注入的 Domain port 使用,这样换实现/换模型不需要改本 module。
 */
public class {pascal}(private val llm: Llm) {{
    public suspend fun run(query: String): String = llm.complete(query)
}}
"""


def _inject_settings(text: str, domains: list[str]) -> str:
    if SENTINEL_SETTINGS not in text:
        raise SystemExit(f"settings.gradle.kts 模板缺少哨兵 {SENTINEL_SETTINGS!r}。")
    includes = "\n".join(f'include(":{d}")' for d in domains)
    return text.replace(SENTINEL_SETTINGS, includes if domains else "")


def _inject_app_deps(text: str, domains: list[str]) -> str:
    if SENTINEL_APP_DEPS not in text:
        raise SystemExit(f"app/build.gradle.kts 模板缺少哨兵 {SENTINEL_APP_DEPS!r}。")
    deps = "\n    ".join(f'implementation(project(":{d}"))' for d in domains)
    return text.replace(SENTINEL_APP_DEPS, deps if domains else "")


def _make_domain_module(target: Path, app_id: str, pkg_path: str, name: str) -> None:
    mod = target / name
    src = mod / "src" / "main" / "kotlin" / pkg_path / name
    src.mkdir(parents=True, exist_ok=True)
    (mod / "build.gradle.kts").write_text(
        _domain_build_gradle().replace("__DOMAIN__", name), encoding="utf-8"
    )
    (mod / "CLAUDE.md").write_text(_domain_claude_md(name), encoding="utf-8")
    (src / f"{_pascal(name)}.kt").write_text(_domain_source(app_id, name), encoding="utf-8")


def scaffold(app_id: str, target: Path, domains: list[str]) -> None:
    if not _valid_app_id(app_id):
        raise SystemExit(
            f"applicationId 非法(需 ≥2 段、每段小写字母开头、非关键字):{app_id!r}。例:com.example.notes"
        )

    seen: set[str] = set()
    for dom in domains:
        if not _valid_domain(dom):
            raise SystemExit(
                f"领域名非法(小写字母开头、其后小写字母/数字、非关键字):{dom!r}。例:--domains retrieval generation"
            )
        if dom in _RESERVED_MODULES:
            raise SystemExit(f"领域名与内置 module 冲突:{dom!r}。请换名。")
        if dom in seen:
            raise SystemExit(f"领域名重复:{dom!r}。")
        seen.add(dom)

    if target.exists() and any(target.iterdir()):
        raise SystemExit(f"目标目录非空:{target}。请换一个空目录或不存在的路径。")

    pkg_path = app_id.replace(".", "/")

    # 1. 整树镜像:内容替换 __APP_ID__;路径替换 __PKG_PATH__。
    for src in TEMPLATES.rglob("*"):
        if not src.is_file():
            continue
        rel = str(src.relative_to(TEMPLATES)).replace(PKG_PATH_PLACEHOLDER, pkg_path)
        dst = target / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        text = src.read_text(encoding="utf-8").replace(APP_ID_PLACEHOLDER, app_id)
        if src.name == "settings.gradle.kts":
            text = _inject_settings(text, domains)
        elif rel == str(Path("app") / "build.gradle.kts"):
            text = _inject_app_deps(text, domains)
        dst.write_text(text, encoding="utf-8")
        if src.name.endswith(".sh"):
            dst.chmod(dst.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

    # 2. 领域 feature module 骨架(只依赖 :domain + :kernel)。
    for dom in domains:
        _make_domain_module(target, app_id, pkg_path, dom)

    # 3.(可选)生成 Gradle wrapper —— 本机有 gradle 时;无则优雅跳过。
    if shutil.which("gradle"):
        try:
            subprocess.run(
                ["gradle", "wrapper", "--gradle-version", GRADLE_VERSION],
                cwd=target,
                check=True,
                capture_output=True,
                text=True,
            )
            print(f"✓ 已生成 Gradle wrapper(gradle {GRADLE_VERSION})")
        except subprocess.CalledProcessError as exc:
            print("⚠ gradle wrapper 生成失败(可稍后手动 `gradle wrapper --gradle-version " + GRADLE_VERSION + "`):")
            print((exc.stderr or exc.stdout or "").strip())
    else:
        print("⚠ 未找到 gradle:请装好后在项目根跑 `gradle wrapper --gradle-version " + GRADLE_VERSION + "` 生成 wrapper。")

    print(f"✓ 已生成 Gradle multi-module 项目:{target}")
    print(f"  applicationId:{app_id}")
    print(f"  领域 module:{', '.join(domains) if domains else '(无)'}")
    print("  下一步:")
    print(f"    cd {target}")
    print(f"    gradle wrapper --gradle-version {GRADLE_VERSION}   # 若上面未自动生成")
    print("    ./ci.sh                # 完整零警告门(ktlint → detekt → 编译(-Werror)→ test)")


def main() -> None:
    ap = argparse.ArgumentParser(
        description="按 android-project-standard 生成 Gradle multi-module(module-per-domain)骨架。",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "app_id 用作 applicationId / namespace / 基础包名(dotted)。\n"
            "领域名用作 Gradle module 名 + 包段,约定小写,如:--domains retrieval generation"
        ),
    )
    ap.add_argument("app_id", help="applicationId(dotted,如 com.example.notes)")
    ap.add_argument("--target", default=".", help="目标目录(默认:当前目录下 <最后一段>/)")
    ap.add_argument(
        "--domains",
        nargs="*",
        default=["retrieval", "generation"],
        metavar="DOMAIN",
        help="领域 module 名(默认:retrieval generation)。传 `--domains` 不带值则不生成领域。",
    )
    args = ap.parse_args()

    base = Path(args.target).resolve()
    target = base / args.app_id.split(".")[-1] if args.target == "." else base
    scaffold(args.app_id, target, list(args.domains))


if __name__ == "__main__":
    main()
