#!/usr/bin/env python3
"""检查一个 Gradle multi-module 项目是否符合 android-project-standard 的关键结构不变量。

用法:
    python check_conformance.py [PROJECT_ROOT]   # 默认当前目录

退出码非 0 表示有违规;适合放进 CI 或 pre-commit。
`ci.sh`(ktlint + detekt + compile -Werror + test)那条门管行为与质量;本脚本管结构。

Gradle 没有 `dump-package` 那样干净的 manifest JSON 出口(`gradle :help` 太重且需 JDK/SDK),
因此本脚本对 build.gradle.kts / settings.gradle.kts 做**文本/正则**近似检查 —— 与 swift 标准
用 `swift package dump-package` 不同,但对结构不变量足够。需要权威解析时可改用
`./gradlew :module:dependencies`,但那需要可用的 Android SDK + JDK,代价高。
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# 厂商 / 重型 SDK 黑名单:Kotlin/Android 生态 LLM / 向量库 / ML SDK 的 Maven 坐标片段(小写子串)。
# `:domain`(及任何领域 feature)的 build.gradle.kts 出现任一即违规(核心抽象零 SDK;实现放 :adapters)。
SDK_DENYLIST = frozenset({
    "com.aallam.openai", "openai", "anthropic", "generativeai", "google-genai",
    "cohere", "mistral", "ollama", "replicate", "groq",
    "langchain4j", "langchain", "dev.langchain",
    "pinecone", "qdrant", "weaviate", "chromadb", "milvus",
    "huggingface", "onnxruntime", "tensorflow", "pytorch", "executorch",
    "mlkit", "com.google.mlkit", "llama", "whisper",
})

# 框架黑名单:`:domain` 必须零框架(纯 kotlin("jvm") 库,不碰 Android / Compose / Hilt)。
DOMAIN_FRAMEWORK_TOKENS = ("com.android", "compose", "hilt", "dagger", "androidx")

# 逃生舱禁令:detekt.yml 必须把这些设为 error(机械可查的核心纪律)。
DETEKT_ESCAPE_RULES = ("UnsafeCallOnNullableType", "UnsafeCast")

# ci.sh 必须串起的门(每项给若干同义关键词,命中其一即满足)。
CI_GATES = (
    ("format(ktlint)", ("ktlintcheck", "ktlint")),
    ("lint(detekt)", ("detekt",)),
    ("compile(-Werror)", ("compiledebugkotlin", "compilekotlin", "assemble", "build")),
    ("test", ("test",)),
)

_INCLUDE_RE = re.compile(r'include\(\s*["\']:([\w:\-]+)["\']\s*\)')


def _module_dir(root: Path, gradle_path: str) -> Path:
    """Gradle 路径 `:a:b` → 目录 a/b。"""
    return root.joinpath(*gradle_path.split(":"))


def _discover_modules(root: Path) -> list[Path]:
    """扫描含 build.gradle.kts 的子目录(排除根、build/、.gradle/)作为 module。"""
    mods: list[Path] = []
    for gradle in root.rglob("build.gradle.kts"):
        d = gradle.parent
        if d == root:
            continue
        parts = set(d.relative_to(root).parts)
        if "build" in parts or ".gradle" in parts:
            continue
        mods.append(d)
    return sorted(mods)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def check(root: Path) -> list[str]:
    problems: list[str] = []

    # 1. 必备根工程文件。
    required = [
        ("settings.gradle.kts", "Gradle 模块注册"),
        ("build.gradle.kts", "根构建(插件 + 两 lint gate)"),
        ("gradle/libs.versions.toml", "version catalog(钉死版本)"),
        ("config/detekt/detekt.yml", "detekt 配置(逃生舱禁令)"),
        (".editorconfig", "ktlint 格式规则"),
        ("ci.sh", "唯一零警告门"),
        ("CLAUDE.md", "根级路由表"),
    ]
    for rel, why in required:
        if not (root / rel).is_file():
            problems.append(f"缺少 {rel}({why})。")

    settings_text = _read(root / "settings.gradle.kts")
    root_build = _read(root / "build.gradle.kts")
    catalog = _read(root / "gradle" / "libs.versions.toml")
    detekt_yml = _read(root / "config" / "detekt" / "detekt.yml")
    editorconfig = _read(root / ".editorconfig")
    ci = _read(root / "ci.sh")

    # 2. multi-module:settings 至少 include 两个 module。
    includes = _INCLUDE_RE.findall(settings_text)
    if len(includes) < 2:
        problems.append(
            f"settings.gradle.kts 仅 include 了 {len(includes)} 个 module(需 ≥2,multi-module)。"
        )

    # 3. 模块发现 + 每个 module 有 CLAUDE.md。
    modules = _discover_modules(root)
    if not modules:
        problems.append("未发现任何含 build.gradle.kts 的 module(应为 Gradle multi-module)。")
    module_names = {m.name for m in modules}
    for m in modules:
        if not (m / "CLAUDE.md").is_file():
            rel = m.relative_to(root)
            problems.append(f"{rel} 缺少 CLAUDE.md(每个 module 需就近契约)。")

    # 4. :domain 存在且零 SDK / 零框架 / 不依赖 :adapters。
    domain_build = root / "domain" / "build.gradle.kts"
    if "domain" not in module_names or not domain_build.is_file():
        problems.append("缺少 `:domain` module(模型无关的核心抽象,零 SDK 零框架)。")
    else:
        text = _read(domain_build).lower()
        sdk_hit = sorted({s for s in SDK_DENYLIST if s in text})
        if sdk_hit:
            problems.append(
                f":domain 依赖了 SDK {sdk_hit}:domain 必须零 SDK,provider 实现放 :adapters。"
            )
        fw_hit = sorted({t for t in DOMAIN_FRAMEWORK_TOKENS if t in text})
        if fw_hit:
            problems.append(
                f":domain 引入了框架 {fw_hit}:domain 必须零框架(纯 kotlin(\"jvm\"),不碰 Android/Compose/Hilt)。"
            )
        if 'project(":adapters")' in text or "project(':adapters')" in text:
            problems.append(":domain 依赖了 :adapters(依赖方向必须单向:domain ← adapters,绝不反向)。")

    # 5. allWarningsAsErrors:根 subprojects 配了,或每个 module 自己配了。
    root_has_wae = "allwarningsaserrors" in root_build.lower()
    if not root_has_wae:
        for m in modules:
            mb = _read(m / "build.gradle.kts").lower()
            if "allwarningsaserrors" not in mb:
                rel = m.relative_to(root)
                problems.append(
                    f"{rel}/build.gradle.kts 未开 allWarningsAsErrors(根 subprojects 也未配)。"
                )

    # 6. detekt.yml:逃生舱规则 + error severity + 失败阈值。
    if detekt_yml:
        for rule in DETEKT_ESCAPE_RULES:
            if rule not in detekt_yml:
                problems.append(f"detekt.yml 未见逃生舱规则 `{rule}`(应 active + severity: error)。")
        if "severity: error" not in detekt_yml.replace("severity:error", "severity: error"):
            problems.append("detekt.yml 未见任何 `severity: error`(逃生舱须设为 error)。")
        low = detekt_yml.lower()
        has_maxissues_zero = bool(re.search(r"maxissues:\s*0", low))
        has_fail_on_sev = "failonseverity" in low
        if not (has_maxissues_zero or has_fail_on_sev):
            problems.append(
                "detekt.yml 未设失败阈值(应 `maxIssues: 0` 或 `failOnSeverity`,否则 finding 不阻断)。"
            )

    # 7. ci.sh:set -euo pipefail + 串四道门。
    if ci:
        if "set -euo pipefail" not in ci:
            problems.append("ci.sh 缺 `set -euo pipefail`。")
        low = ci.lower()
        for label, keywords in CI_GATES:
            if not any(kw in low for kw in keywords):
                problems.append(f"ci.sh 未串起 {label} 门(未见关键词:{' / '.join(keywords)})。")

    # 8. libs.versions.toml:钉 kotlin + detekt + ktlint。
    if catalog:
        low = catalog.lower()
        if "kotlin" not in low:
            problems.append("libs.versions.toml 未钉 kotlin 版本。")
        if "detekt" not in low:
            problems.append("libs.versions.toml 未声明 detekt(lint gate 插件)。")
        if "ktlint" not in low:
            problems.append("libs.versions.toml 未声明 ktlint(格式 gate 插件)。")

    # 9. 生成绑定 gate-excluded(仅当存在生成目录时检查)。
    generated_dirs = [
        d for d in root.rglob("*")
        if d.is_dir() and d.name in ("uniffi", "generated")
        and "build" not in d.relative_to(root).parts
        and ".gradle" not in d.relative_to(root).parts
    ]
    if generated_dirs:
        excluded = any(
            ("uniffi" in blob or "generated" in blob)
            and ("exclude" in blob or "ktlint = disabled" in blob)
            for blob in (root_build.lower(), detekt_yml.lower(), editorconfig.lower())
        )
        if not excluded:
            rels = sorted(str(d.relative_to(root)) for d in generated_dirs)
            problems.append(
                f"发现生成绑定目录 {rels} 但未在 detekt/ktlint 配置里排除"
                "(polyglot-core-standard 第 4 条:generated bindings 须 gate-excluded)。"
            )

    return problems


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not root.is_dir():
        print(f"✗ 路径不存在或不是目录:{root}")
        return 2
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
